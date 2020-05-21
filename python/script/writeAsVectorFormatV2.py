'''
# プロジェクトファイルに含まれている複数レイヤーを指定範囲でクリッピング(実はIntersect)して別名のGeoPackageで保存する

'''

import os
import subprocess
from qgis.core import *

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

# データソースのプロジェクトファイル
project = QgsProject.instance()

# 東京都500mメッシュ別将来推計人口と東京都バス停のshapeファイル
# http://nlftp.mlit.go.jp/ksj/gml/datalist/KsjTmplt-mesh500h30.html
project.read('../500m_mesh.qgz')
print("入力："+ project.fileName())
absolutePath = project.absolutePath()

# QGISのブックマークエディタで画面表示されている四隅座標を取得
filterExtent = QgsRectangle(139.708694789, 35.642186746, 139.770192591, 35.695803397)

# 出力DB名
outputFileName = absolutePath + "\\output.gpkg"
print("出力：" + outputFileName)

# 1ループ目は上書き
appendMode = False

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

        # key:valueにセット
        layerId[layer.id()] = layer.name()
        
        save_options = QgsVectorFileWriter.SaveVectorOptions()
        save_options.fileEncoding = "UTF-8"
        save_options.layerName = layer.name()

        # 一回目はDBを作成
        if appendMode :
            save_options.actionOnExistingFile = QgsVectorFileWriter.CreateOrOverwriteLayer

        appendMode = True

        # IntersectでClipではなかったorz
        save_options.filterExtent = filterExtent
 
        transform_context = QgsProject.instance().transformContext()

        # GeoPackageに出力
        error = QgsVectorFileWriter.writeAsVectorFormatV2(layer,
                                                          outputFileName,
                                                          transform_context,
                                                          save_options)
        if error[0] == QgsVectorFileWriter.NoError:
            print("writeAsVectorFormatV2 success!")
        elif error[0] == QgsVectorFileWriter.ErrDriverNotFound :
            print("ErrDriverNotFound !")
        elif error[0] == QgsVectorFileWriter.ErrCreateDataSource  :
            print("ErrCreateDataSource  !")
        elif error[0] == QgsVectorFileWriter.ErrCreateLayer  :
            print("ErrCreateLayer  !")
        elif error[0] == QgsVectorFileWriter.ErrAttributeTypeUnsupported  :
            print("ErrAttributeTypeUnsupported  !")
        elif error[0] == QgsVectorFileWriter.ErrAttributeCreationFailed  :
            print("ErrAttributeCreationFailed  !")
        elif error[0] == QgsVectorFileWriter.ErrProjection  :
            print("ErrProjection  !")
        elif error[0] == QgsVectorFileWriter.ErrFeatureWriteFailed   :
            print("ErrFeatureWriteFailed   !")
        elif error[0] == QgsVectorFileWriter.ErrInvalidLayer   :
            print("ErrInvalidLayer   !")
        else:
             print("Canceled ")

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

newproject.write()

print("処理終了")

qgs.exitQgis()
