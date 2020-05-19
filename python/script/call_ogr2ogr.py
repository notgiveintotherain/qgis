'''
# プロジェクトファイルに含まれている複数レイヤーを指定範囲でクリッピングして別名のGeoPackageで保存する

'''

import os
import subprocess
from qgis.core import *
# VisualStudio ソリューション検索パスで
# %QGIS_INSTALL%/apps/qgis-ltr/python/plugins/processingを追加すること
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

# データソースのプロジェクトファイル
project = QgsProject.instance()

# 東京都500mメッシュ別将来推計人口と東京都バス停のshapeファイル
# http://nlftp.mlit.go.jp/ksj/gml/datalist/KsjTmplt-mesh500h30.html
project.read('../500m_mesh.qgz')
print("入力："+ project.fileName())
absolutePath = project.absolutePath()

# QGISのブックマークエディタで画面表示されている四隅座標を取得
clipextent = "139.708694789 35.642186746 139.770192591 35.695803397"

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


        # ogrドライバが対応するデータソースかどうかチェックする
        layername = GdalUtils.ogrLayerName(layer.dataProvider().dataSourceUri())
        if not layername:
           print("未サポートのデータソース:" + layer.name())
           break

        # key:valueにセット
        layerId[layer.id()] = layername

        # テストなのでCRS未定義の場合強制的にEPSG:4612に設定
        sourceCrs = layer.sourceCrs()
        if sourceCrs != "EPSG:4612":
            sourceCrs = "EPSG:4612"

        # ogrogrコマンド引数
        cmd = ("ogr2ogr {} -f \"GPKG\" {} -a_srs \"{}\" -clipsrc {} {}".
                format(appendSwitch, outputFileName, sourceCrs, clipextent, layer.source()))
        print (cmd)

        # ogrogrコマンド実行
        runcmd = subprocess.check_call(cmd)
        print (runcmd)

        # ２回目以降はこのスイッチを付けないと常に上書きになってしまう
        appendSwitch = "-append"
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

newproject.write()

print("処理終了")

qgs.exitQgis()