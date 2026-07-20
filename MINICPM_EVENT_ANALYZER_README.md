# MiniCPM-V 事件分析脚本

这个小包不需要服务器安装 Codex。脚本只使用 Python 标准库，直接连接已经运行的两个服务：

- HTTP Event Receiver：`http://127.0.0.1:18090`
- MiniCPM-V：`http://127.0.0.1:18091`

它会读取 Receiver 事件和图片，请 MiniCPM-V 输出结构化 JSON，并原子写入：

```text
/home/qi/va-test/http-events-v2/<eventDirectory>/analysis/minicpm-v-4.6.json
```

## 1. 解压到仓库

在服务器执行：

```bash
cd ~/vlm-yolo-deploy-record
unzip -o ~/minicpm-event-analyzer-bundle.zip
chmod +x scripts/minicpm_event_analyzer.py
```

压缩包会新增以下文件，不会覆盖 Receiver：

```text
scripts/minicpm_event_analyzer.py
tests/test_minicpm_event_analyzer.py
MINICPM_EVENT_ANALYZER_README.md
```

## 2. 运行单元测试

```bash
cd ~/vlm-yolo-deploy-record
python -m unittest tests/test_minicpm_event_analyzer.py -v
```

## 3. 检查两个服务

```bash
curl -i http://127.0.0.1:18090/health
curl -i http://127.0.0.1:18091/health
```

两个命令都应返回 `HTTP/1.1 200 OK`。

## 4. 分析事件

分析当前最新事件：

```bash
python scripts/minicpm_event_analyzer.py --latest --overwrite
```

分析指定事件：

```bash
python scripts/minicpm_event_analyzer.py \
  --message-id 1d854bb0-53b4-480e-98a1-dd247c6535be \
  --overwrite
```

成功时终端会显示实际结果文件路径，例如：

```json
{"output":"/home/qi/va-test/http-events-v2/20260717/1d854bb0-53b4-480e-98a1-dd247c6535be/analysis/minicpm-v-4.6.json","status":"ok"}
```

查看结果：

```bash
python -m json.tool \
  /home/qi/va-test/http-events-v2/20260717/1d854bb0-53b4-480e-98a1-dd247c6535be/analysis/minicpm-v-4.6.json
```

## 5. 可选配置

默认值可用环境变量覆盖：

```bash
export VA_RECEIVER_URL=http://127.0.0.1:18090
export VA_VLM_URL=http://127.0.0.1:18091
export VA_EVENT_DIR=/home/qi/va-test/http-events-v2
export VA_VLM_MODEL=/models/MiniCPM-V-4.6
```

运行 `python scripts/minicpm_event_analyzer.py --help` 可查看全部参数。

## 说明

- 图片选择顺序：标注图 `annotated` → 原图 `original` → 检测图 `detected`。
- 请求固定携带 `downsample_mode=16x` 和 `max_slice_nums=1`，用于规避当前 Transformers 服务处理 1280×720 图片时出现的多切片 shape 错误。
- 模型被要求严格区分“图片可见事实”和“风险推断”。
- 如果模型没有返回合法 JSON，脚本仍保存 `status=parse_error`、原始回复和错误原因，方便排查。
- 未加 `--overwrite` 时不会覆盖已有分析结果。
