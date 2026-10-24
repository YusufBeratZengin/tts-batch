# tts-batch

UTF-8 metin betiklerini yerel seslendirmeye, numaralandırılmış cümle WAV dosyalarına ve JSON altyazı zaman çizelgesine dönüştürün.

[![CI](https://github.com/YusufBeratZengin/tts-batch/actions/workflows/ci.yml/badge.svg)](https://github.com/YusufBeratZengin/tts-batch/actions/workflows/ci.yml)
[![PyPI version](https://img.shields.io/pypi/v/tts-batch.svg?color=blue)](https://pypi.org/project/tts-batch/)
[![Python 3.10+](https://img.shields.io/badge/python-3.10%2B-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)

[English](README.md) · [Katkı Rehberi](CONTRIBUTING.md) · [Değişiklikler](CHANGELOG.md)

<p align="center">
  <img src="docs/demo.svg" alt="tts-batch terminal demosu" width="820">
</p>

## Neden tts-batch?

- **Tamamen çevrimdışı ve yerel**: Piper (ONNX), espeak-ng veya Kokoro ile tamamen yerel iş istasyonunuzda çalışır. Sıfır API anahtarı, sırsız mimari, aylık abonelik ücreti yok ve hiçbir ses verisi dışarı çıkmaz.
- **Video kurgu ve altyazı uyumlu**: DaVinci Resolve, Premiere veya altyazı araçlarına doğrudan sürüklenebilen numaralı cümle WAV dosyaları (`0001.wav`, `0002.wav`, ...) ile birlikte birleşik `narration.wav` ve tam kare hassasiyetinde JSON zaman çizelgesi üretir.
- **Saf standart kütüphane çekirdeği**: Çekirdek paket hiçbir dış çalışma zamanı bağımlılığı gerektirmez. Doğrudan diske akış halinde $O(1)$ bellek birleştirmesi, saf Python RMS/tepe normalizasyonu ve deterministik SHA-256 önbellekleme sunar.

## Hızlı başlangıç

### 1. Kurulum

`tts-batch` paketini pip ile kurun:

```sh
# PyPI üzerinden
python -m pip install tts-batch

# Veya yerel repodan
python -m pip install -e .
```

### 2. Metni inceleyin (Kuru çalıştırma)

Ses motorunu çalıştırmadan cümle bölümlerini ve hızları test edin:

```sh
tts-batch render examples/script.md --dry-run
```

Çıktı:
```text
Segment 0001 [voice: (default), speed: 1.00]: Hello, world.
Segment 0002 [voice: (default), speed: 1.00]: This is a short narration.
Segment 0003 [voice: (default), speed: 1.10]: Use the sentence files in your video editor.
Segment 0004 [voice: (default), speed: 1.00]: Keep the timing manifest for captions.
```

### 3. Seslendirmeyi üretin

Sistemdeki yerel `espeak` motorunu kullanarak ses üretin:

```sh
tts-batch render examples/script.md -o out/ --engine espeak --voice en
```

Türkçe kısaltmaları ("yy.", "vb.", "örn.") ve sıra sayılarını ("22. Ekim 2026") içeren Türkçe metni seslendirin:

```sh
tts-batch render examples/script.tr.md -o out/ --engine espeak --voice tr
```

`python -m tts_batch` komutu doğrudan `tts-batch` ile eşdeğerdir.

## Kullanım örnekleri

### Metin biçimi ve yönergeler

Metinler `.txt` veya `.md` biçiminde ve UTF-8 (veya UTF-8 BOM) olarak kodlanmalıdır:

```markdown
# # ile başlayan satırlar yorum olarak yok sayılır
Merhaba dünya. Bu *kısa* bir seslendirme.
[pause 500ms]
[speed 1.1]
Bu bölüm biraz daha hızlı okunur.
[voice models/diger.onnx]
Buradan sonra başka bir ses modeli kullanılır.
```

| Yönerge | Davranış |
| --- | --- |
| `[pause 500ms]` | Sessizlik ekler (milisaniye); `250.5ms` gibi ondalıklı değerler geçerlidir |
| `[speed 1.1]` | Sonraki cümlelerin okuma hız çarpanını belirler; varsayılan `1.0` |
| `[voice yol/veya/id]` | Sonraki metin için ses modelini veya kimliğini belirler; boşluk içerebilir |
| `*vurgu*` | Yıldızlar otomatik ayıklanır; ses motorları tarafından göz ardı edilir |
| `# Yorum` | İlk boşluk dışı karakteri `#` olan satır bütünüyle yok sayılır |

Yönergeler anında etkinleşir ve önceki metni bağımsız bir ses parçasına dönüştürür. Hız ve ses ayarları tekrar değiştirilene kadar geçerliliğini korur.

### Motor seçenekleri

Tercih ettiğiniz ses motorunu ayrı olarak kurun:

1. **Piper (Yapay Zeka Destekli ONNX)**: Yüksek kaliteli yerel yapay zeka sesi. PATH üzerinde `piper`, yerel bir `.onnx` modeli ve modelin yanındaki `.onnx.json` dosyasını gerektirir.
   ```sh
   tts-batch render examples/script.md -o out/ --engine piper --voice models/en_US.onnx
   ```
2. **espeak-ng (Hafif ve hızlı)**: Çok hızlı yerel sentez. PATH üzerinde `espeak-ng` veya `espeak` programını gerektirir.
   ```sh
   # Yüklü dilleri listele
   tts-batch --list-voices

   # Belirli bir dil koduyla çalıştır
   tts-batch render examples/script.md -o out/ --engine espeak --voice en
   ```
3. **Kokoro (İsteğe bağlı ek)**:
   ```sh
   python -m pip install -e ".[kokoro]"
   tts-batch render examples/script.md -o out/ --engine kokoro \
     --kokoro-model models/kokoro-v1_0.pth \
     --kokoro-config models/config.json --voice voices/af_heart.pt --lang a
   ```
   Yerel `.pth` ağırlık dosyası, yapılandırma JSON'ı ve `.pt` ses tensörü gerektirir. Çevrimdışı güvenlik için adaptör `HF_HUB_OFFLINE=1` ve `TRANSFORMERS_OFFLINE=1` tanımlar. Desteklenen diller: `a` (ABD İngilizcesi), `b` (BK İngilizcesi), `e` (İspanyolca), `f` (Fransızca), `h` (Hintçe), `i` (İtalyanca), `p` (Portekizce), `z` (Mandarin).

### Python API

Betikleri doğrudan Python kodunuzdan da çalıştırabilirsiniz:

```python
from pathlib import Path
from tts_batch import render
from tts_batch.engines import EspeakEngine

manifest = render(
    "Merhaba dünya. Bu Python seslendirmesidir.",
    Path("out"),
    EspeakEngine(),
    voice="tr",
    gap=0.2,
    normalization="rms",
    target_db=-20.0,
)
print(f"Seslendirilen cümle sayısı: {len(manifest['sentences'])}, dosya: {manifest['audio']}")
```

## Yapılandırma

### Komut satırı seçenekleri

```sh
tts-batch render <script.md> -o <cikti_klasoru> [secenekler]
```

| Seçenek | Varsayılan | Açıklama |
| --- | --- | --- |
| `-o, --output` | *(zorunlu)* | Çıktı dosyalarının ve manifestin yazılacağı klasör |
| `--engine` | `espeak` | Ses motoru adaptörü (`piper`, `espeak`, `kokoro`) |
| `--voice` | `""` | Ses modeli dosya yolu (Piper/Kokoro) veya dil kodu (espeak) |
| `--speed` | `1.0` | Genel konuşma hızı çarpanı (> 0) |
| `--gap` | `0.2` | Parçalar arasına eklenecek sessizlik boşluğu (saniye) |
| `--normalize` | `rms` | Ses normalizasyonu yöntemi: `rms`, `peak` veya `none` |
| `--target-db` | `-20.0` | Hedef dBFS seviyesi (-120 ile 0 dBFS arası) |
| `--dry-run` | `false` | Ses sentezleme yapmadan cümle bölümlerini ekrana yazdırır |
| `--list-voices` | `false` | Sistemde yüklü `espeak-ng` seslerini listeler |
| `--cache-dir` | `OUTPUT/.cache` | Deterministik WAV önbellek klasörü |
| `--no-cache` | `false` | Önbelleği devre dışı bırakır ve yeniden sentezler |

### Çıktı yapısı ve manifest şeması

Her çalıştırma sonucunda çıktı klasöründe şu dosyalar oluşur:

```text
out/
  0001.wav          # İlk cümlenin ses dosyası
  0002.wav          # İkinci cümlenin ses dosyası
  narration.wav     # Boşluklar ve duraklamalar dahil birleşik ses
  manifest.json     # Zamanlama üstverisi ve altyazı hizalaması
  .cache/           # SHA-256 sentez önbelleği
```

`tts-batch render` komutu tamamlandığında kısa bir durum özeti yazdırır:

```text
Rendered 2 segments (2.000s) to out/
```

Oluşan `out/manifest.json` dosyası cümle ve tahmini kelime zamanlamalarını sağlar:

```json
{
  "schema_version": 1,
  "engine": "stub",
  "audio": "narration.wav",
  "sample_rate": 16000,
  "channels": 1,
  "duration": 2.0,
  "frames": 32000,
  "gap_seconds": 0.2,
  "normalization": "rms",
  "target_dbfs": -20.0,
  "word_timing": "estimated_character_weight",
  "sentences": [
    {
      "text": "Hello, world.",
      "file": "0001.wav",
      "voice": "",
      "speed": 1.0,
      "start": 0.0,
      "end": 0.6,
      "start_frame": 0,
      "end_frame": 9600,
      "duration": 0.6,
      "cache_hit": false,
      "cache_key": "a362ec42341e2f77fcff42ef970afa0c3adfe7b02accbdb38310db9892b79e65",
      "words": [
        {
          "text": "Hello",
          "start": 0.0,
          "end": 0.3
        },
        {
          "text": "world",
          "start": 0.3,
          "end": 0.6
        }
      ]
    },
    {
      "text": "This is a short narration.",
      "file": "0002.wav",
      "voice": "",
      "speed": 1.0,
      "start": 0.8,
      "end": 2.0,
      "start_frame": 12800,
      "end_frame": 32000,
      "duration": 1.2,
      "cache_hit": false,
      "cache_key": "10ced23c9fd24e29c4c8ff3463649d65f8881d21f74ba4db47c70632945f40c7",
      "words": [
        {
          "text": "This",
          "start": 0.8,
          "end": 1.0285625
        },
        {
          "text": "is",
          "start": 1.0285625,
          "end": 1.142875
        },
        {
          "text": "a",
          "start": 1.142875,
          "end": 1.2
        },
        {
          "text": "short",
          "start": 1.2,
          "end": 1.4856875
        },
        {
          "text": "narration",
          "start": 1.4856875,
          "end": 2.0
        }
      ]
    }
  ]
}
```

## SSS ve Sınırlamalar

- **Ses biçimi gereksinimleri**: Tüm motor çıktıları sıkıştırılmamış 16 bit PCM WAV olmalıdır. Tek bir çalıştırmadaki tüm parçaların örnekleme hızı ve kanal sayısı aynı olmalıdır (otomatik yeniden örnekleme yapılmaz).
- **Kelime zamanlaması tahmini**: Cümle sınırları WAV ses karelerinden tam kesinlikle hesaplanır. Kelime zamanları ise karakter ağırlıklı tahmindir (`word_timing: "estimated_character_weight"`); zorunlu akustik hizalama (forced alignment) değildir.
- **Motor programları ve modeller**: Bu paket motor ikililerini (`espeak`, `piper`) veya ses modellerini indirmez ve dağıtmaz. Motor lisansları projenin MIT lisansından bağımsızdır.
- **Eşzamanlılık ve dizin güvenliği**: Çıktı dosyaları hazırlanıp ardından `narration.wav` ve `manifest.json` güncellenir. Ancak dosya sistemi düzeyindeki klasör değişimi atomik değildir; aynı çıktı klasörüne eşzamanlı çalıştırma yapmayın.

## Katkıda Bulunma

Katkılarınızı memnuniyetle kabul ediyoruz!

```sh
# Geliştirme ortamını hazırlayın
python -m pip install -e ".[dev]"

# Kod stili ve biçimlendirmeyi kontrol edin
python -m ruff check .
python -m ruff format --check .

# Katı tip denetimini çalıştırın
python -m mypy

# Test paketini kapsam raporu ile çalıştırın
python -m pytest --cov=tts_batch
```

Ayrıntılı bilgi için [CONTRIBUTING.md](CONTRIBUTING.md) ve güvenlik ilkeleri için [SECURITY.md](SECURITY.md) dosyalarına bakın.

## Lisans

Bu proje [MIT Lisansı](LICENSE) kapsamında sunulmaktadır.
