'''
# プロジェクトファイルに含まれている複数レイヤーを指定範囲でクリッピングして別名のGeoPackageで保存する

'''

import os
import subprocess
from qgis.core import *
# VisualStudio ソリューション検索パスで
# %QGIS_INSTALL%/apps/qgis-ltr/python/plugins/processingを追加すること
import processing 
from processing.core.Processing import Processing
from processing.algs.gdal.GdalUtils import GdalUtils

# 環境変数を設定
# https://gis.stackexchange.com/questions/326968/ogr2ogr-error-1-proj-pj-obj-create-cannot-find-proj-db
os.environ['QT_QPA_PLATFORM_PLUGIN_PATH'] = r'C:\Program Files\QGIS 3.10\apps\Qt5\plugins'
os.environ['GDAL_DATA'] = r'c:\Program Files\QGIS 3.10\share\gdal'
os.environ['GDAL_DRIVER_PATH'] = r'c:\Program Files\QGIS 3.10\bin\gdalplugins'
os.environ['PROJ_LIB'] = r'c:\Program Files\QGIS 3.10\share\proj'

# スタンドアロンスクリプトを起動するためのおまじない。
# https://docs.qgis.org/2.14/ja/docs/pyqgis_developer_cookbook/intro.html
QgsApplication.setPrefixPath("C:\Program Files\QGIS 3.10\bin", True)
qgs = QgsApplication([], True)
qgs.initQgis()

# Processing初期化
Processing.initialize()

# データソースのプロジェクトファイル
project = QgsProject.instance()

# 東京都500mメッシュ別将来推計人口と東京都バス停のshapeファイル
# http://nlftp.mlit.go.jp/ksj/gml/datalist/KsjTmplt-mesh500h30.html
project.read('../500m_mesh.qgz')
print("入力："+ project.fileName())
absolutePath = project.absolutePath()

# QGISのブックマークエディタで画面表示されている四隅座標を取得
clipextent = QgsRectangle(139.708694789, 35.642186746, 139.770192591, 35.695803397)

uri = "polygon?crs={}&field=id:integer".format("EPSG:4612");
cliplayer = QgsVectorLayer(uri, "clippolygon",  "memory");
fields = cliplayer.fields()
feature = QgsFeature(fields)
feature.setGeometry(QgsGeometry.fromRect(clipextent))

cliplayer.startEditing()
feature['id'] = 1
ret = cliplayer.addFeature(feature)
cliplayer.commitChanges()

# GeoPackageに出力
save_options = QgsVectorFileWriter.SaveVectorOptions()
save_options.actionOnExistingFile = QgsVectorFileWriter.CreateOrOverwriteFile
save_options.fileEncoding = "UTF-8"
save_options.layerName = cliplayer.name()
transform_context = QgsProject.instance().transformContext()
clippingPolygon =  absolutePath + "\\clip.gpkg"
error = QgsVectorFileWriter.writeAsVectorFormatV2(cliplayer,
                                                    clippingPolygon,
                                                    transform_context,
                                                    save_options)

# 出力DB名
outputFileName = absolutePath + "\\output.gpkg"
print("出力：" + outputFileName)

# 1ループ目は上書き
appendSwitch = ""

# レイヤリスト保存 
layers = project.mapLayers()

# LayerID:LayerNameのkey:value
layerId = {}

print("Clipping開始")

for layer in layers.values():
    if layer.type() == QgsMapLayerType.VectorLayer:
        print("name:" + layer.name())
        print("source:" + layer.source())
        print("id:" + layer.id())


        layername = GdalUtils.ogrLayerName(layer.dataProvider().dataSourceUri())
        if not layername:
           print("未サポートのデータソース:" + layer.name())
           break

        # key:valueにセット
        layerId[layer.id()] = layername
        
        outputlayer = QgsProcessingOutputLayerDefinition(outputFileName)
        option = ("{}".format(appendSwitch))
        params = { 
            'INPUT' : layer,
            'EXTENT' : cliplayer, # QgsRectangle指定はエラーとなる 敢えてQgsVectorLayer指定
            'OPTIONS': option,
            'OUTPUT' : outputlayer
        }

        res = processing.run('gdal:clipvectorbyextent', params)
        appendSwitch = "-append" # ogr2ogrのオプション

        if not res:
            print("processing failed:" + layer.name())
            break
    else:
        print("Is not vetorlayer:" + layer.name())


# 指定範囲でエクスポートしたDBを再度読み込みsetDataSourceで参照先DBを変更
print("プロジェクトファイルのデータソース書き換え開始")

# プロジェクトファイルをrename
newproject = QgsProject.instance()
newproject.write(absolutePath + "\\output.qgz")
print("出力：" + newproject.fileName())

for layerid in layerId.items():
    fullname = outputFileName + "|layername=" + layerid[1]

    display_name = layerid[1]

    # レイヤIDで検索
    tagetlayer = newproject.mapLayer(layerid[0])

    print("dataSource :" + fullname)
    print("baseName :" + display_name)
    print("RelacelayerID:" + tagetlayer.id())

    # データソース書換
    provider_options = QgsDataProvider.ProviderOptions()
    provider_options.transformContext = newproject.transformContext()
    tagetlayer.setDataSource(fullname, display_name, "ogr", provider_options)

# clipした領域のベクタレイヤを追加
cliplayer = QgsVectorLayer(clippingPolygon, "clippolygon", "ogr")
if not cliplayer.isValid():
    print("レイヤのロード失敗!")
else:
    newproject.addMapLayer(cliplayer)

newproject.write()

print("処理終了")

