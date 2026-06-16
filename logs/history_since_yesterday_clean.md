 1252  -m .../Qwen3VL-2B-Instruct-F16.gguf
 1253  Qwen3VL-2B-Instruct-F16.gguf
 1254  ./build/bin/llama-cli   -m /home/lee-server/.cache/modelscope/hub/models/Qwen/Qwen3-VL-2B-Instruct-GGUF/Qwen3VL-2B-Instruct-Q4_K_M.gguf   -p "你好，介绍一下你自己"
 1255  ./build/bin/llama-cli   -m Q4_K_M.gguf   --mmproj mmproj-F16.gguf   -p "描述这张图片"
 1256  ls -lh /home/lee-server/a.png
 1257  cd ~/llama.cpp
 1258  ./build/bin/llama-cli --help | grep -i image
 1259  ./build/bin/llama-cli   -m /home/lee-server/.cache/modelscope/hub/models/Qwen/Qwen3-VL-2B-Instruct-GGUF/Qwen3VL-2B-Instruct-Q4_K_M.gguf   --mmproj /home/lee-server/.cache/modelscope/hub/models/Qwen/Qwen3-VL-2B-Instruct-GGUF/mmproj-Qwen3VL-2B-Instruct-F16.gguf   --image /home/lee-server/a.png   -p "请详细描述这张图片，并指出图中主要目标。"
 1260  mkdir -p ~/yolov8
 1261  cd ~/yolov8
 1263  cd ~/yolov8
 1264  pip install -U ultralytics opencv-python-headless -i https://pypi.tuna.tsinghua.edu.cn/simple
 1265  python - << 'PY'
 1266  from ultralytics import YOLO
 1267  model = YOLO("yolo26n.pt")
 1268  print("YOLO26 加载成功")
 1269  PY
 1270  yolo predict model=yolo26n.pt source=/home/lee-server/a.png conf=0.25 imgsz=960
 1271  ls runs/detect/predict
 1272  cd ~/llama.cpp
 1273  cat > yolo_qwen_image_demo.py << 'PY'
 1274  import os
 1275  import cv2
 1276  import subprocess
 1277  from ultralytics import YOLO
 1278  # ===== 路径配置 =====
 1279  IMAGE_PATH = "/home/lee-server/a.png"
 1280  YOLO_MODEL = "/home/lee-server/yolov8/yolo26n.pt"
 1281  LLAMA_CLI = "/home/lee-server/llama.cpp/build/bin/llama-cli"
 1282  QWEN_MODEL = "/home/lee-server/.cache/modelscope/hub/models/Qwen/Qwen3-VL-2B-Instruct-GGUF/Qwen3VL-2B-Instruct-Q4_K_M.gguf"
 1283  MMPROJ = "/home/lee-server/.cache/modelscope/hub/models/Qwen/Qwen3-VL-2B-Instruct-GGUF/mmproj-Qwen3VL-2B-Instruct-F16.gguf"
 1284  OUTPUT_IMAGE = "/home/lee-server/yolo_qwen_result.jpg"
 1285  def run_yolo():
 1286      model = YOLO(YOLO_MODEL)
 1287      results = model.predict(
 1288          source=IMAGE_PATH,
 1289          conf=0.25,
 1290          imgsz=960,
 1291          verbose=True
 1292      )
 1293      r = results[0]
 1294      names = r.names
 1295      img = cv2.imread(IMAGE_PATH)
 1296      if img is None:
 1297          raise RuntimeError(f"图片读取失败：{IMAGE_PATH}")
 1298      yolo_lines = []
 1299      if r.boxes is None or len(r.boxes) == 0:
 1300          yolo_summary = "YOLO26 未检测到明确目标。"
 1301      else:
 1302          for i, box in enumerate(r.boxes):
 1303              cls_id = int(box.cls[0])
 1304              conf = float(box.conf[0])
 1305              label = names[cls_id]
 1306              x1, y1, x2, y2 = map(int, box.xyxy[0].tolist())
 1307              yolo_lines.append(
 1308                  f"目标{i}: 类别={label}, 置信度={conf:.2f}, 位置=({x1},{y1},{x2},{y2})"
 1309              )
 1310              cv2.rectangle(img, (x1, y1), (x2, y2), (0, 255, 0), 2)
 1311              cv2.putText(
 1312                  img,
 1313                  f"{label} {conf:.2f}",
 1314                  (x1, max(20, y1 - 10)),
 1315                  cv2.FONT_HERSHEY_SIMPLEX,
 1316                  0.7,
 1317                  (0, 255, 0),
 1318                  2
 1319              )
 1320          yolo_summary = "\n".join(yolo_lines)
 1321      cv2.imwrite(OUTPUT_IMAGE, img)
 1322      return yolo_summary
 1323  def run_qwen(yolo_summary):
 1324      prompt = f"""
 1325  你是一个视觉语言多模态安全分析助手。
 1326  YOLO26 已经对图片进行了目标检测，检测结果如下：
 1327  {yolo_summary}
 1328  请结合整张图片和 YOLO 检测结果，用中文完成以下分析：
 1329  1. 图片中主要有哪些目标？
 1330  2. YOLO26 的检测结果是否合理？
 1331  3. 人和车辆之间是否存在潜在风险？
 1332  4. 如果这是道路监控、机器人巡检或工业安全场景，应该给出什么安全提醒？
 1333  5. 请给出一句简洁的报警/提示语。
 1334  要求：回答清晰、分点说明，不要重复废话。
 1335  """
 1336      cmd = [
 1337          LLAMA_CLI,
 1338          "-m", QWEN_MODEL,
 1339          "--mmproj", MMPROJ,
 1340          "--image", IMAGE_PATH,
 1341          "-p", prompt,
 1342          "-n", "512"
 1343      ]
 1344      result = subprocess.run(
 1345          cmd,
 1346          stdout=subprocess.PIPE,
 1347          stderr=subprocess.STDOUT,
 1348          text=True
 1349      )
 1350      return result.stdout
 1351  def main():
 1352      print("=" * 80)
 1353      print("[1] 开始 YOLO26 目标检测")
 1354      yolo_summary = run_yolo()
 1355      print("=" * 80)
 1356      print("[YOLO26 检测结果]")
 1357      print(yolo_summary)
 1358      print("=" * 80)
 1359      print(f"[检测结果图已保存] {OUTPUT_IMAGE}")
 1360      print("=" * 80)
 1361      print("[2] 开始 Qwen3-VL 综合分析")
 1362      qwen_answer = run_qwen(yolo_summary)
 1363      print("=" * 80)
 1364      print("[Qwen3-VL 分析结果]")
 1365      print(qwen_answer)
 1366  if __name__ == "__main__":
 1367      main()
 1368  PY
 1369  cd ~/llama.cpp
 1370  python yolo_qwen_image_demo.py
 1371  ls -lh /home/lee-server/test.mp4
 1372  ls -lh test.mp4
 1373  find /home/lee-server -type f \( -iname "*.mp4" -o -iname "*.avi" -o -iname "*.mov" -o -iname "*.mkv" -o -iname "*.flv" \) -exec ls -lh {} \; 2>/dev/null
 1374  ffprobe /home/lee-server/test.mp4
 1375  sudo apt install ffmpeg
 1376  cd ~/llama.cpp
 1377  ls single_video_yolo.py
 1378  exit
 1379  ffmpeg -re -stream_loop -1   -i /home/lee-server/test.mp4   -c:v libx264 -preset veryfast -tune zerolatency   -an   -f rtsp rtsp://127.0.0.1:8554/cam1
 1380  ffmpeg -re -stream_loop -1   -i /home/lee-server/test.mp4   -c:v libx264 -preset veryfast -tune zerolatency   -an   -f rtsp   -rtsp_transport tcp   rtsp://127.0.0.1:8554/cam1
 1381  sudo docker ps | grep mediamtx
 1382  nohup ffmpeg -re -stream_loop -1   -i /home/lee-server/test.mp4   -c copy   -an   -f rtsp   -rtsp_transport tcp   rtsp://127.0.0.1:8554/cam1   > /home/lee-server/cam1_push.log 2>&1 &
 1383  tail -n 30 /home/lee-server/cam1_push.log
 1384  ffprobe -rtsp_transport tcp rtsp://127.0.0.1:8554/cam1
 1385  cd ~/llama.cpp
 1386  python - << 'PY'
 1387  path = "single_video_yolo.py"
 1388  with open(path, "r", encoding="utf-8") as f:
 1389      s = f.read()
 1390  old = '''    if not os.path.exists(source):
 1391          raise FileNotFoundError(f"找不到视频：{source}")
 1392  '''
 1393  new = '''    is_stream = source.startswith(("rtsp://", "rtmp://", "http://", "https://"))
 1394      if not is_stream and not os.path.exists(source):
 1395          raise FileNotFoundError(f"找不到视频：{source}")
 1396  '''
 1397  if old in s:
 1398      s = s.replace(old, new)
 1399      print("已修改：single_video_yolo.py 支持 RTSP/网络流输入")
 1400  else:
 1401      print("未找到原始检查语句，可能已经改过了")
 1402  with open(path, "w", encoding="utf-8") as f:
 1403      f.write(s)
 1404  PY
 1405  grep -n "is_stream\|os.path.exists(source)" single_video_yolo.py
 1406  cd ~/llama.cpp
 1407  OPENCV_FFMPEG_CAPTURE_OPTIONS="rtsp_transport;tcp" python single_video_yolo.py   --source rtsp://127.0.0.1:8554/cam1   --output /home/lee-server/rtsp_yolo_output.mp4   --max-frames 100
 1408  ls -lh /home/lee-server/rtsp_yolo_output.mp4
 1409  pkill -f "rtsp://127.0.0.1:8554/cam1"
 1410  ps aux | grep ffmpeg
 1411  sudo docker ps | grep mediamtx
 1412  nohup ffmpeg -re -stream_loop -1   -i /home/lee-server/test.mp4   -vf "scale=1280:-2,fps=12"   -c:v libx264 -preset veryfast -tune zerolatency   -an   -f rtsp   -rtsp_transport tcp   rtsp://127.0.0.1:8554/cam1   > /home/lee-server/cam1_push.log 2>&1 &
 1413  tail -n 30 /home/lee-server/cam1_push.log
 1414  ffprobe -rtsp_transport tcp rtsp://127.0.0.1:8554/cam1
 1415  cd ~/llama.cpp
 1416  OPENCV_FFMPEG_CAPTURE_OPTIONS="rtsp_transport;tcp" python single_video_yolo.py   --source rtsp://127.0.0.1:8554/cam1   --output /home/lee-server/rtsp_yolo_1280_output.mp4   --max-frames 300
 1417  cd ~/llama.cpp
 1418  OPENCV_FFMPEG_CAPTURE_OPTIONS="rtsp_transport;tcp" python single_video_yolo.py   --source rtsp://127.0.0.1:8554/cam1   --output /home/lee-server/rtsp_yolo_1280_imgsz640_output.mp4   --imgsz 640   --max-frames 300
 1419  nohup ffmpeg -re -stream_loop -1   -ss 00:01:00   -i /home/lee-server/test.mp4   -vf "scale=1280:-2,fps=12"   -c:v libx264 -preset veryfast -tune zerolatency   -an   -f rtsp   -rtsp_transport tcp   rtsp://127.0.0.1:8554/cam2   > /home/lee-server/cam2_push.log 2>&1 &
 1420  ffprobe rtsp://127.0.0.1:8554/cam1
 1421  nohup ffmpeg -re -stream_loop -1   -ss 00:02:00   -i /home/lee-server/test.mp4   -vf "scale=1280:-2,fps=12"   -c:v libx264 -preset veryfast -tune zerolatency   -an   -f rtsp   -rtsp_transport tcp   rtsp://127.0.0.1:8554/cam3   > /home/lee-server/cam3_push.log 2>&1 &
 1422  ps aux | grep ffmpeg
 1423  for cam in cam1 cam2 cam3; do   echo "===== $cam =====";   ffprobe -v error -rtsp_transport tcp     -select_streams v:0     -show_entries stream=width,height,r_frame_rate     -of default=noprint_wrappers=1     rtsp://127.0.0.1:8554/$cam; done
 1424  cd ~/llama.cpp
 1425  cat > multi_rtsp_yolo.py << 'PY'
 1426  import os
 1427  import cv2
 1428  import time
 1429  import argparse
 1430  from urllib.parse import urlparse
 1431  from ultralytics import YOLO
 1432  def stream_name(url: str) -> str:
 1433      path = urlparse(url).path.strip("/")
 1434      return path.replace("/", "_") if path else "stream"
 1435  def open_capture(source: str):
 1436      cap = cv2.VideoCapture(source, cv2.CAP_FFMPEG)
 1437      cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
 1438      if not cap.isOpened():
 1439          raise RuntimeError(f"无法打开视频流：{source}")
 1440      width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH)) or 1280
 1441      height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT)) or 720
 1442      fps = cap.get(cv2.CAP_PROP_FPS)
 1443      if not fps or fps <= 1:
 1444          fps = 12.0
 1445      return cap, width, height, fps
 1446  def main():
 1447      parser = argparse.ArgumentParser()
 1448      parser.add_argument(
 1449          "--sources",
 1450          nargs="+",
 1451          default=[
 1452              "rtsp://127.0.0.1:8554/cam1",
 1453              "rtsp://127.0.0.1:8554/cam2",
 1454              "rtsp://127.0.0.1:8554/cam3",
 1455          ],
 1456          help="多路RTSP地址"
 1457      )
 1458      parser.add_argument("--model", default="/home/lee-server/yolov8/yolo26n.pt")
 1459      parser.add_argument("--output-dir", default="/home/lee-server/multi_yolo_outputs")
 1460      parser.add_argument("--conf", type=float, default=0.25)
 1461      parser.add_argument("--imgsz", type=int, default=640)
 1462      parser.add_argument("--max-frames", type=int, default=300)
 1463      args = parser.parse_args()
 1464      os.makedirs(args.output_dir, exist_ok=True)
 1465      print("=" * 80)
 1466      print("[启动] 多路 RTSP YOLO26 检测")
 1467      print(f"[模型] {args.model}")
 1468      print(f"[推理尺寸] imgsz={args.imgsz}")
 1469      print(f"[路数] {len(args.sources)}")
 1470      print("=" * 80)
 1471      model = YOLO(args.model)
 1472      caps = []
 1473      writers = []
 1474      names = []
 1475      counts = []
 1476      fourcc = cv2.VideoWriter_fourcc(*"mp4v")
 1477      for source in args.sources:
 1478          name = stream_name(source)
 1479          cap, width, height, fps = open_capture(source)
 1480          output_path = os.path.join(args.output_dir, f"{name}_detect.mp4")
 1481          writer = cv2.VideoWriter(output_path, fourcc, fps, (width, height))
 1482          if not writer.isOpened():
 1483              raise RuntimeError(f"无法创建输出视频：{output_path}")
 1484          caps.append(cap)
 1485          writers.append(writer)
 1486          names.append(name)
 1487          counts.append(0)
 1488          print(f"[打开] {name}: {source}")
 1489          print(f"       分辨率={width}x{height}, FPS={fps}, 输出={output_path}")
 1490      start_time = time.time()
 1491      try:
 1492          while True:
 1493              frames = []
 1494              active_indices = []
 1495              for i, cap in enumerate(caps):
 1496                  if counts[i] >= args.max_frames:
 1497                      continue
 1498                  ret, frame = cap.read()
 1499                  if not ret:
 1500                      print(f"[警告] {names[i]} 读取失败，跳过这一帧")
 1501                      continue
 1502                  frames.append(frame)
 1503                  active_indices.append(i)
 1504              if not frames:
 1505                  break
 1506              results = model.predict(
 1507                  frames,
 1508                  conf=args.conf,
 1509                  imgsz=args.imgsz,
 1510                  verbose=False
 1511              )
 1512              for result, idx in zip(results, active_indices):
 1513                  plotted = result.plot()
 1514                  writers[idx].write(plotted)
 1515                  counts[idx] += 1
 1516              total = sum(counts)
 1517              if total % 30 == 0:
 1518                  elapsed = time.time() - start_time
 1519                  total_fps = total / elapsed if elapsed > 0 else 0
 1520                  status = ", ".join([f"{names[i]}={counts[i]}" for i in range(len(names))])
 1521                  print(f"[进度] 总帧={total}, 总FPS={total_fps:.2f}, {status}")
 1522              if all(c >= args.max_frames for c in counts):
 1523                  break
 1524      finally:
 1525          for cap in caps:
 1526              cap.release()
 1527          for writer in writers:
 1528              writer.release()
 1529      elapsed = time.time() - start_time
 1530      total = sum(counts)
 1531      total_fps = total / elapsed if elapsed > 0 else 0
 1532      print("=" * 80)
 1533      print("[完成] 多路 RTSP YOLO26 检测结束")
 1534      print(f"[总处理帧数] {total}")
 1535      print(f"[总平均FPS] {total_fps:.2f}")
 1536      for i, name in enumerate(names):
 1537          print(f"[{name}] 帧数={counts[i]}, 平均FPS={counts[i] / elapsed:.2f}")
 1538      print(f"[输出目录] {args.output_dir}")
 1539      print("=" * 80)
 1540  if __name__ == "__main__":
 1541      main()
 1542  PY
 1543  OPENCV_FFMPEG_CAPTURE_OPTIONS="rtsp_transport;tcp" python multi_rtsp_yolo.py   --imgsz 640   --max-frames 300
 1544  ls -lh /home/lee-server/multi_yolo_outputs
 1545  pkill -f "rtsp://127.0.0.1:8554/cam"
 1546  ps aux | grep ffmpeg
 1547  nohup ffmpeg -re -stream_loop -1   -i /home/lee-server/test.mp4   -vf "scale=1280:-2,fps=12"   -c:v libx264 -preset veryfast -tune zerolatency   -g 12 -bf 0 -pix_fmt yuv420p   -an   -f rtsp   -rtsp_transport tcp   rtsp://127.0.0.1:8554/cam1   > /home/lee-server/cam1_push.log 2>&1 &
 1548  nohup ffmpeg -re -stream_loop -1   -ss 00:01:00   -i /home/lee-server/test.mp4   -vf "scale=1280:-2,fps=12"   -c:v libx264 -preset veryfast -tune zerolatency   -g 12 -bf 0 -pix_fmt yuv420p   -an   -f rtsp   -rtsp_transport tcp   rtsp://127.0.0.1:8554/cam2   > /home/lee-server/cam2_push.log 2>&1 &
 1549  nohup ffmpeg -re -stream_loop -1   -ss 00:02:00   -i /home/lee-server/test.mp4   -vf "scale=1280:-2,fps=12"   -c:v libx264 -preset veryfast -tune zerolatency   -g 12 -bf 0 -pix_fmt yuv420p   -an   -f rtsp   -rtsp_transport tcp   rtsp://127.0.0.1:8554/cam3   > /home/lee-server/cam3_push.log 2>&1 &
 1550  ps aux | grep ffmpeg
 1551  for cam in cam1 cam2 cam3; do   echo "===== $cam =====";   ffprobe -v error -rtsp_transport tcp     -select_streams v:0     -show_entries stream=width,height,r_frame_rate     -of default=noprint_wrappers=1     rtsp://127.0.0.1:8554/$cam; done
 1552  cd ~/llama.cpp
 1553  OPENCV_FFMPEG_CAPTURE_OPTIONS="rtsp_transport;tcp" python multi_rtsp_yolo.py   --imgsz 640   --max-frames 300
 1554  ls -lh /home/lee-server/multi_yolo_outputs
 1555  pkill -f "rtsp://127.0.0.1:8554/cam"
 1556  ps aux | grep ffmpeg
 1557  sudo docker stop mediamtx
 1558  cd ~/llama.cpp
 1559  python - << 'PY'
 1560  path = "yolo_qwen_image_demo.py"
 1561  with open(path, "r", encoding="utf-8") as f:
 1562      s = f.read()
 1563  old = '''        "-p", prompt,
 1564          "-n", "512"
 1565  '''
 1566  new = '''        "-p", prompt,
 1567          "-n", "512",
 1568          "--no-cnv"
 1569  '''
 1570  if "--no-cnv" not in s:
 1571      s = s.replace(old, new)
 1572  with open(path, "w", encoding="utf-8") as f:
 1573      f.write(s)
 1574  print("已修改：加入 --no-cnv，让 llama-cli 生成后自动退出")
 1575  PY
 1576  python yolo_qwen_image_demo.py
 1577  cd ~/llama.cpp
 1578  python - << 'PY'
 1579  path = "yolo_qwen_image_demo.py"
 1580  with open(path, "r", encoding="utf-8") as f:
 1581      s = f.read()
 1582  # 1. 删除 --no-cnv
 1583  s = s.replace('        "--no-cnv"\n', '')
 1584  s = s.replace('        "--no-cnv",\n', '')
 1585  # 2. 给 subprocess.run 加 input="/exit\\n"
 1586  old = '''    result = subprocess.run(
 1587          cmd,
 1588          stdout=subprocess.PIPE,
 1589          stderr=subprocess.STDOUT,
 1590          text=True
 1591      )
 1592  '''
 1593  new = '''    result = subprocess.run(
 1594          cmd,
 1595          input="/exit\\\\n",
 1596          stdout=subprocess.PIPE,
 1597          stderr=subprocess.STDOUT,
 1598          text=True
 1599      )
 1600  '''
 1601  if 'input="/exit\\\\n",' not in s:
 1602      s = s.replace(old, new)
 1603  with open(path, "w", encoding="utf-8") as f:
 1604      f.write(s)
 1605  print("已修复：删除 --no-cnv，并加入自动 /exit")
 1606  PY
 1607  grep -n "no-cnv\|input=" yolo_qwen_image_demo.py
 1608  python yolo_qwen_image_demo.py
 1609  ls -lh /home/lee-server/test.mp4
 1610  ls single_video_yolo.py
 1611  cd ~/llama.cpp
 1612  cat > single_video_yolo.py << 'PY'
 1613  import os
 1614  import cv2
 1615  import time
 1616  import argparse
 1617  from ultralytics import YOLO
 1618  def run_video(source, model_path, output_path, conf=0.25, imgsz=960, max_frames=300):
 1619      source = os.path.expanduser(source)
 1620      output_path = os.path.expanduser(output_path)
 1621      if not os.path.exists(source):
 1622          raise FileNotFoundError(f"找不到视频：{source}")
 1623      if not os.path.exists(model_path):
 1624          raise FileNotFoundError(f"找不到YOLO模型：{model_path}")
 1625      model = YOLO(model_path)
 1626      cap = cv2.VideoCapture(source)
 1627      if not cap.isOpened():
 1628          raise RuntimeError(f"无法打开视频：{source}")
 1629      width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
 1630      height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
 1631      src_fps = cap.get(cv2.CAP_PROP_FPS)
 1632      if src_fps <= 1 or src_fps != src_fps:
 1633          src_fps = 25
 1634      fourcc = cv2.VideoWriter_fourcc(*"mp4v")
 1635      writer = cv2.VideoWriter(output_path, fourcc, src_fps, (width, height))
 1636      frame_id = 0
 1637      start_time = time.time()
 1638      print("=" * 80)
 1639      print("[启动] 单路视频 YOLO26 检测")
 1640      print(f"[输入视频] {source}")
 1641      print(f"[输出视频] {output_path}")
 1642      print(f"[分辨率] {width}x{height}")
 1643      print(f"[源FPS] {src_fps}")
 1644      print(f"[模型] {model_path}")
 1645      print("=" * 80)
 1646      while True:
 1647          ret, frame = cap.read()
 1648          if not ret:
 1649              break
 1650          frame_id += 1
 1651          results = model.predict(
 1652              source=frame,
 1653              conf=conf,
 1654              imgsz=imgsz,
 1655              verbose=False
 1656          )
 1657          result = results[0]
 1658          annotated = result.plot()
 1659          writer.write(annotated)
 1660          if frame_id % 10 == 0:
 1661              elapsed = time.time() - start_time
 1662              real_fps = frame_id / elapsed if elapsed > 0 else 0
 1663              obj_count = len(result.boxes) if result.boxes is not None else 0
 1664              print(f"[Frame {frame_id}] 处理FPS={real_fps:.2f}, 检测目标数={obj_count}")
 1665          if max_frames > 0 and frame_id >= max_frames:
 1666              print(f"[停止] 已达到 max_frames={max_frames}")
 1667              break
 1668      cap.release()
 1669      writer.release()
 1670      elapsed = time.time() - start_time
 1671      avg_fps = frame_id / elapsed if elapsed > 0 else 0
 1672      print("=" * 80)
 1673      print("[完成] 单路视频 YOLO26 检测结束")
 1674      print(f"[总处理帧数] {frame_id}")
 1675      print(f"[平均处理FPS] {avg_fps:.2f}")
 1676      print(f"[结果视频] {output_path}")
 1677  def main():
 1678      parser = argparse.ArgumentParser()
 1679      parser.add_argument("--source", type=str, default="/home/lee-server/test.mp4")
 1680      parser.add_argument("--model", type=str, default="/home/lee-server/yolov8/yolo26n.pt")
 1681      parser.add_argument("--output", type=str, default="/home/lee-server/yolo_video_output.mp4")
 1682      parser.add_argument("--conf", type=float, default=0.25)
 1683      parser.add_argument("--imgsz", type=int, default=960)
 1684      parser.add_argument("--max-frames", type=int, default=300)
 1685      args = parser.parse_args()
 1686      run_video(
 1687          source=args.source,
 1688          model_path=args.model,
 1689          output_path=args.output,
 1690          conf=args.conf,
 1691          imgsz=args.imgsz,
 1692          max_frames=args.max_frames
 1693      )
 1694  if __name__ == "__main__":
 1695      main()
 1696  PY
 1697  ls -lh single_video_yolo.py
 1698  python single_video_yolo.py   --source /home/lee-server/test.mp4   --output /home/lee-server/yolo_video_output.mp4   --max-frames 300
 1699  ls -lh /home/lee-server/yolo_video_output.mp4
 1700  sudo apt update
 1701  sudo apt install -y ffmpeg
 1702  ffmpeg -version
 1703  docker run --rm -it --network host bluenviron/mediamtx:latest
 1704  sudo apt install -y docker.io
 1705  sudo systemctl start docker
 1706  sudo systemctl enable docker
 1707  sudo docker run --rm -it --network host bluenviron/mediamtx:latest
 1708  ffmpeg -version
 1709  cd /home/lee-server
 1710  mkdir -p docker/mediamtx
 1711  cd docker/mediamtx
 1712  wget https://github.com/bluenviron/mediamtx/releases/download/v1.18.2/mediamtx_v1.18.2_linux_amd64.tar.gz
 1713  tar -zxvf mediamtx_v1.18.2_linux_amd64.tar.gz
 1714  ls -lh
 1715  cat > Dockerfile << 'EOF'
 1716  FROM scratch
 1717  COPY mediamtx /mediamtx
 1718  COPY mediamtx.yml /mediamtx.yml
 1719  EXPOSE 8554
 1720  EXPOSE 1935
 1721  EXPOSE 8888
 1722  EXPOSE 8889
 1723  EXPOSE 8890/udp
 1724  EXPOSE 8189/udp
 1725  ENTRYPOINT ["/mediamtx", "/mediamtx.yml"]
 1726  EOF
 1727  cat Dockerfile
 1728  sudo docker build -t local/mediamtx:1.18.2 .
 1729  sudo docker images | grep mediamtx
 1730  sudo docker run --rm -it   --network host   --name mediamtx   local/mediamtx:1.18.2
 1731  ip addr
 1732  sudo apt update
 1733  sudo apt install -y openssh-server
 1734  sudo systemctl start ssh
 1735  sudo systemctl enable ssh
 1736  sudo systemclt status ssh
 1737  sudo systemctl status ssh
 1738  hostname -I
 1739  cd ~/llama.cpp
 1740  ls
 1741  cd ~
 1742  mkdir -p vlm-yolo-deploy-record/{logs,scripts,results,notes}
 1743  cd vlm-yolo-deploy-record
 1744  cd ~
 1745  mkdir -p vlm-yolo-deploy-record/{logs,scripts,results,notes}
 1746  cd vlm-yolo-deploy-record
 1747  cp ~/llama.cpp/yolo_qwen_image_demo.py scripts/
 1748  cp ~/llama.cpp/single_video_yolo.py scripts/
 1749  cp ~/llama.cpp/multi_rtsp_yolo.py scripts/
 1750  ls scripts
 1751  history | tail -n 500 > logs/history_since_yesterday_raw.txt
