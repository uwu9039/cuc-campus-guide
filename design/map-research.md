# 校园地图数据调研（2026-10-29）

产出 `campus-map.json`：36 个 POI，有坐标 28（high 10 / medium 18 / low 8）。lat/lng 为 GCJ-02，wgs84 另列。中心取均值 39.9126/116.5580，与任务给的 39.909~39.911 有偏差，以实测 POI 为准。

## 来源
- 高德网页 POI：立德楼 `B0FFKHN1MM`、博学楼 `B0FFHUU1AY`、艺传大楼 `B0K0UZXD1C`、图书馆 `B000AA0V9S`，链接 `amap.com/place/<id>`，high。
- OSM：24 条，`source_url` 均指向 `openstreetmap.org/way|node/<id>`（经 Photon 检索/反查），楼体中心而非门点，high/medium。
- 官方：`cuc.edu.cn/tsxy/list.htm`（楼名）、问道 `1b97d899`（位置表）、`cd72bce4`（简称）、`4b3b7735`（场馆）、`00f4cdcc`（图书馆手册）、`5ee0f0ae`（场馆办法）、`48e1da04`（梯控）。
- 博学楼 1 层 3 女 1 男厕所：`source=user`。

高德与 OSM 同点位差 50–150 m（POI 点 vs 楼体中心），已写入各条 `note`。

## 没查到（null，不估算）
南门、西门、21 号楼、44 号楼、中传学术中心、中传音乐厅、基本伙食堂、快递驿站。

## 建议确认
1. 21/44 号楼现场补点；2. 卡务中心：官方写艺传 1 层，任务写 44 号楼；3. OSM 在 2 号楼后方只有一栋“演播厅”，演播馆与学术中心取其一（现判给演播馆）；4. 大学生活动中心 OSM 有两处候选；5. 音乐厅、快递柜无楼栋；6. 无障碍设施官方无数据。

## 接入
`app.py` 的 `/api/campus` 读 `sources/campus-pois.json`（无坐标），按 `name` 把本文件的 `lat/lng/aliases/confidence/facilities` 并进去即可。本次未改 app.py、index.html、items.json；未使用任何 API Key。
