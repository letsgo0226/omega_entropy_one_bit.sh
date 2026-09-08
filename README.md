# omega_entropy_one_bit.sh

[![Omega Entropy One Bit](https://github.com/letsgo0226/omega_entropy_one_bit.sh/actions/workflows/omega-entropy.yml/badge.svg)](https://github.com/letsgo0226/omega_entropy_one_bit.sh/actions/workflows/omega-entropy.yml)

在「啟動時取樣一次公平位元、之後保留同一位元」的機率模型下，每個固定步數的抽象狀態分布具有 **1 bit 香農熵**。主程式為 1,510 bytes 的單行 Shell／Python 程式，保留可逆編碼與 OMEGA 核心。

## 使用

~~~sh
sh omega_entropy_one_bit.sh 8
~~~

預設執行 8 輪，輸出一筆模型說明及八筆 JSON 狀態。iSH 可透過原有的 apk 分支安裝 Python；macOS 請先備妥 python3。程式使用 Python 標準函式庫。

參數 0 表示不設定迭代上限，可按 Ctrl+C 結束。歷史狀態會在記憶體累積，仍受實際資源限制。GitHub Actions 固定使用有限的 8 輪。

## 1 bit 的精確意思

令 $B$ 是啟動時抽取的一個公平位元，$P(B=0)=P(B=1)=1/2$。令 $d_n$ 是由程式與步數決定的路徑歷史，$S_n=(d_n,B)$。

兩個候選狀態的 BIT 尾碼始終不同，因此對每個有限 $n\geq1$，在已知程式、輸入與步數、尚未觀察到 $B$ 的模型下：

$$H(S_n \mid \text{程式、輸入、}n)=H(B)=1\text{ bit}.$$

同一位元會一直保留，所以整段有限歷史的模型熵也只有 1 bit。觀察到 $B$ 後，剩餘條件熵為 0；下一步不會新增獨立的隨機資訊。

公平性是亂數來源的模型假設。程式透過 [Python secrets.randbits](https://docs.python.org/3/library/secrets.html) 取樣，並明確輸出 RNG_PHYSICAL_ENTROPY_VERIFIED=false。此程式沒有測量整台電腦或物理系統的總熵。

| 欄位 | 意義 |
|---|---|
| BIT | 本次啟動所抽取的 0 或 1，同一次執行內保持不變 |
| H_MODEL_BITS | 合併相同候選結果的機率後，計算所得的模型熵 |
| DISTINCT | 兩個候選狀態仍可區分 |
| REV | 兩個候選都通過 D(E(S))=S |
| RETURN | 候選狀態的第一行仍是 OMEGA 核心 |
| SPEC_OK | 本輪指定條件全部通過，失敗時以非零狀態退出 |
| TABLEAU_LITERAL_CHECK | 檢查原有字串表內的矛盾標记，不是一般用途的邏輯證明器 |

## GitHub Actions：事件驅動與每五分鐘排程

[Workflow](.github/workflows/omega-entropy.yml) 同時啟用：

| 觸發方式 | 執行時機 |
|---|---|
| push | 每次推送提交 |
| pull_request | 建立、更新提交或重新開啟 Pull Request |
| workflow_dispatch | Actions 頁面手動執行 |
| schedule | cron 為 */5 * * * *，每五分鐘安排一次 |

排程採 UTC，每小時的 00、05、10……55 分啟動排程。[GitHub 官方文件](https://docs.github.com/en/actions/reference/workflows-and-actions/events-that-trigger-workflows#schedule)說明排程可能因負載延遲，部分排隊工作可能被丟棄，因此不是精確的 300 秒計時器。

每次工作最多執行 5 分鐘；同一分支有較新的觸發時，會取消舊的重疊工作。Workflow 權限為 contents: read。它只輸出執行紀錄與摘要，沒有上傳 artifact 或把執行產物提交回儲存庫。

## 驗證

~~~sh
sh -n omega_entropy_one_bit.sh
python3 tests/verify_entropy_model.py
~~~

驗證器除了執行腳本，也枚舉 B=0 與 B=1 兩種來源情況，直接檢查每輪的狀態 bytes、整段軌跡、可逆編碼與核心；不只讀取程式自行回報的 SPEC_OK。

驗證包含：

- 一個實體行，且檔案小於 2,048 bytes。
- 每次啟動僅呼叫一次隨機來源，8 輪後結束。
- 兩個公平候選及整段歷史的模型熵均為 1 bit。
- 空資料、前導零與高位元組可完整編碼回返。
- 將機率改為 3/4、1/4 時，算出約 0.811278 bit 並拒絕。
- 將兩個候選合併時，算出 0 bit 並拒絕。

有限測試用於發現實作錯誤；所有有限步數的模型結論，依據是「同一個公平位元被保留，兩個候選始終可區分」的構造。
