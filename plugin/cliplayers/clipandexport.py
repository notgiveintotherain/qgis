# -*- coding: utf-8 -*-
"""
/***************************************************************************
 ExportProcessing
                                 A QGIS plugin
 表示は範囲をGeoPackageにエクスポートする
                              -------------------
        begin                : 2020-04-28
        git sha              : $Format:%H$
        copyright            : (C) 2020 by インクリメントP株式会社
        email                : yonezawa@incrementp.co.jp
 ***************************************************************************/

/***************************************************************************
 *                                                                         *
 *   This program is free software; you can redistribute it and/or modify  *
 *   it under the terms of the GNU General Public License as published by  *
 *   the Free Software Foundation; either version 2 of the License, or     *
 *   (at your option) any later version.                                   *
 *                                                                         *
 ***************************************************************************/
"""

import os
#import subprocess,shlex
from qgis.PyQt.QtCore import QObject, pyqtSlot, pyqtSignal
from qgis.core import *

import processing 
from processing.core.Processing import Processing,GdalAlgorithmProvider
from processing.algs.gdal.GdalUtils import GdalUtils

class ClipByExtent(QObject):
    exportError = pyqtSignal(unicode)
    exportMessage = pyqtSignal(unicode)
    exportProcessed = pyqtSignal(int)
    exportFinished = pyqtSignal()

    Processing.initialize()
    QgsApplication.processingRegistry().addProvider(GdalAlgorithmProvider())
    #print(processing.algorithmHelp("gdal:clipvectorbyextent"))

    def __init__(self):
        QObject.__init__(self)

    def setOutputGpkgPath(self, filePath):
        self.gpkgPath = filePath

    def setOutputProjectPath(self, filePath):
        self.qgisProjectpath = filePath

    def setMinMaxClear(self, minmaxclear):
        self.minmaxclear = minmaxclear

    def setExtent(self, extent):
        self.extent = extent

    def clipAndExport(self):
        project = QgsProject.instance()
        self.exportMessage.emit("入力："+ project.fileName())

		# クリッピング範囲
        #clipextent = self.extent.toString().replace(","," ").replace(":"," ")
        #clipextent = ("{},{},{},{}").format(
        #                    self.extent.xMinimum(), # 順番に要注意
        #                    self.extent.xMaximum(), # 順番に要注意
        #                    self.extent.yMinimum(), # 順番に要注意
        #                    self.extent.yMaximum()) # 順番に要注意

        self.exportMessage.emit("extent:" + self.extent.toString())

		# 1ループ目は上書き
        appendSwitch = ""

		# レイヤリスト保存 ソースがPostgreSQLの場合はここでｘ
		# ソースレイヤのパスが./となっているとErrInvalidLayerになる
        layers = project.mapLayers()

        # DBのエクスポートと接続情報書き換えで2倍
        cnt = project.count()
        total = 100 / (cnt * 2)

		# LayerID:LayerName
        layerId = {}

        self.exportMessage.emit("Clipping開始")

        # Clip用形状を作成する
        uri = "polygon?crs={}&field=id:integer".format("EPSG:4612");
        cliplayer = QgsVectorLayer(uri, "clippolygon",  "memory");
        fields = cliplayer.fields()
        feature = QgsFeature(fields)
        feature.setGeometry(QgsGeometry.fromRect(self.extent))
        cliplayer.startEditing()
        feature['id'] = 1
        ret = cliplayer.addFeature(feature)
        cliplayer.commitChanges()

        # GeoPackageに出力(デバッグ用)
        #save_options = QgsVectorFileWriter.SaveVectorOptions()
        #save_options.actionOnExistingFile = QgsVectorFileWriter.CreateOrOverwriteFile
        #save_options.fileEncoding = "UTF-8"
        #save_options.layerName = cliplayer.name()
        #transform_context = QgsProject.instance().transformContext()
        #error = QgsVectorFileWriter.writeAsVectorFormatV2(cliplayer,
        #                                                    "c:\\DMP\\overlay.gpkg",
        #                                                    transform_context,
        #                                                    save_options)

        index = 0
        for layer in layers.values():
            if layer.type() == QgsMapLayerType.VectorLayer:
                
                self.exportMessage.emit("name:" + layer.name())
                self.exportMessage.emit("source:" + layer.source())
                self.exportMessage.emit("id:" + layer.id())

                layername = GdalUtils.ogrLayerName(layer.dataProvider().dataSourceUri())
                if not layername:
                    self.exportMessage.emit("未サポートのデータソース:" + layer.name())
                    break

                #layerId[layer.id()] = layername
                # PostGIS->GPKGの場合 gdal:clipvectorbyextent でogr2orすると
                # [schema].[tablename]->[tablename]とschema名無のテーブル名になるため
                layerId[layer.id()] = layer.name()

                outputlayer = QgsProcessingOutputLayerDefinition(self.gpkgPath)
                #'OPTIONS': -a_srsをつけるとエラーになる
                option = ("{}".format(appendSwitch))
                params = { 
                    'INPUT' : layer,
                    #'EXTENT' : clipextent,
                    'EXTENT' : cliplayer,
                    'OPTIONS': option,
                    'OUTPUT' : outputlayer
                }   

                res = processing.run('gdal:clipvectorbyextent', params)
                if not res:
                    self.exportError.emit("processing failed:" + layer.name())
                    break

                '''
                dataSource = ""
                sourceProvider = layer.storageType()
                if sourceProvider == "GPKG":
                    dataSource = layer.source().replace("|layername=", " ")
                elif sourceProvider.find("PostGIS"):
                    result = layer.source().split()
                    self.exportMessage.emit(result)

                    connection = {}
                    for token in result:
                        token2 = token.split("=")
                        if len(token2) == 2:
                            connection[token2[0]] = token2[1]

                    dbName = connection.get("dbname")
                    hostName = connection.get("host")
                    portNo = connection.get("port")
                    usrName = connection.get("user")
                    passWord = connection.get("password")
                    tableName = connection.get("table")
                    if passWord == None:
                        passWord = usrName

                    dataSource = ("PG:\"host={} port={} dbname={} user={} password={}\" {}".
                                    format(hostName, portNo, dbName, usrName, passWord, tableName))
            
                sourceCrs = layer.sourceCrs()

                cmd = ("ogr2ogr {} -f \"GPKG\" {} -a_srs \"{}\" -clipsrc {} {}".
                        format(appendSwitch, self.gpkgPath, sourceCrs.authid(), clipextent, dataSource))

                #runcmd = subprocess.check_call(cmd)
                runcmd = subprocess.run(cmd, 
                                        stdout=subprocess.PIPE, 
                                        stdin=subprocess.DEVNULL, 
                                        stderr=subprocess.STDOUT,
                                        universal_newlines=True)
                self.exportMessage.emit (runcmd)
                '''

                appendSwitch = "-append"
                
            self.exportProcessed.emit(int(index * total))
            index += 1

        #プロジェクトファイルをrename
        newproject = QgsProject.instance()
        newproject.write(self.qgisProjectpath)
        self.exportMessage.emit("出力：" + newproject.fileName())

        # 指定範囲でエクスポートしたDBを再度読み込みsetDataSourceで参照先DBを変更
        self.exportMessage.emit("プロジェクトファイルのデータソース書き換え開始")
        for layerid in layerId.items():
            fullname = self.gpkgPath + "|layername=" + layerid[1]

            display_name = layerid[1]
            tagetlayer = newproject.mapLayer(layerid[0])
            provider_options = QgsDataProvider.ProviderOptions()
            # Use project's transform context
            provider_options.transformContext = newproject.transformContext()

            self.exportMessage.emit("dataSource :" + fullname)
            self.exportMessage.emit("baseName :" + display_name)
            self.exportMessage.emit("RelacelayerID:" + tagetlayer.id())

            tagetlayer.setDataSource(fullname, display_name, "ogr", provider_options)

            # min max Zoom level設定をクリアする
            if self.minmaxclear:
                if tagetlayer.hasScaleBasedVisibility():
                    tagetlayer.setScaleBasedVisibility(False)

            self.exportProcessed.emit(int(index * total))
            index += 1

        newproject.write()
        self.exportMessage.emit("プロジェクトファイルのデータソース書き換え終了")
        self.exportProcessed.emit(100)

        self.exportFinished.emit()

