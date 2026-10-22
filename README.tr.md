# tts-batch

UTF-8 metinlerden yerel seslendirme, cümle başına WAV dosyası ve altyazı zaman
çizelgesi üretir. Python 3.10 veya üzeri gerekir. Çekirdek paket yalnızca Python
standart kütüphanesini kullanır.

[English](README.md) · [Katkı rehberi](CONTRIBUTING.md) · [Değişiklikler](CHANGELOG.md)

## Kurulum ve kullanım

Depo kökünde:

```sh
python -m pip install -e .
tts-batch render examples/script.md -o out/ --engine espeak --voice en
tts-batch render examples/script.tr.md -o out/ --engine espeak --voice tr
tts-batch render script.md -o out/ --engine piper --voice models/tr_TR.onnx
```

`python -m tts_batch` komutu da kullanılabilir. Varsayılan motor `espeak`, PATH
üzerindeki `espeak-ng` veya `espeak` programını çalıştırır. Piper için PATH
üzerinde `piper`, yerel bir `.onnx` model dosyası ve yanında `.onnx.json`
yapılandırması bulunmalıdır. Motor programlarını ve modelleri önceden kendiniz
kurmalısınız; bu paket model indirmez. Motorların ve ses modellerinin lisansları
projenin MIT lisansından ayrıdır.

Bulut hesabı veya ücretli API gerekmez. Seçilen motor bulunamazsa komut hata
verir. Yedek motoru kullanmak için `--engine espeak` seçin.

## Metin biçimi

`.txt` ve `.md` dosyaları desteklenir. CLI, UTF-8 BOM işaretini de kabul eder.

```text
# Bu satır okunmaz
Merhaba dünya. Bu *kısa* bir seslendirme.
[pause 500ms]
[speed 1.1]
Bu bölüm biraz daha hızlı okunur.
[voice models/diger.onnx]
Buradan sonra başka bir ses kullanılır.
```

| İşaret | Davranış |
| --- | --- |
| `[pause 500ms]` | 500 milisaniye sessizlik ekler; ondalıklı değer kabul edilir |
| `[speed 1.1]` | Sonraki metnin hız çarpanını değiştirir; varsayılan 1.0 |
| `[voice x]` | Sonraki metnin sesini değiştirir; dosya yolunda boşluk olabilir |
| `*vurgu*` | Yıldızlar kaldırılır; motorlara vurgu uygulanmaz |
| İlk boşluk dışı karakteri `#` olan satır | Satır bütünüyle atlanır |

Yönergeler büyük/küçük harfe duyarlıdır. Her yönerge, kendisinden önce biriken
metni ayrı ses parçasına dönüştürür. Cümlenin ortasında kullanılırsa cümle
bölünür. Hız ve ses ayarı tekrar değiştirilene kadar geçerlidir. Köşeli
parantezler yönergelere ayrılmıştır; bilinmeyen, eksik veya hatalı yönergeler
reddedilir. Diğer Markdown özellikleri işlenmez. Satır sonları boşluğa dönüşür;
cümleler noktalama işaretleriyle ayrılır.

Cümle ayırıcı yaygın Türkçe/İngilizce kısaltmaları, baş harfleri, ondalık
sayıları, Latin noktalamasını ve Çince/Japonca tam genişlikli işaretleri tanır.
Boşlukla ayrılan Kiril metinlerinde de çalışır. Kurallara dayalıdır; belirsiz
kısaltmalarda, sıra sayılarında veya farklı dil kurallarında elle sınır koymak
gerekebilir. Bunun için `[pause 0ms]` kullanılabilir.

## Çıktı ve zamanlar

`out/` içinde `0001.wav`, `0002.wav` gibi ses parçaları, birleşik
`narration.wav`, `manifest.json` ve varsayılan `.cache/` önbelleği oluşur.
Numaralı dosyalar yalnızca konuşmayı içerir. Birleşik dosya, baştaki ve sondaki
duraklamaları, metin içindeki duraklamaları ve parçalar arasındaki boşluğu da
içerir. `[pause ...]` ile `--gap` süreleri toplanır. İlk parçadan önce ve son
parçadan sonra otomatik boşluk eklenmez.

Manifestte şema sürümü, motor, birleşik dosyanın adı, örnekleme hızı, kanal
sayısı, toplam süre ve kare sayısı bulunur. `sentences` listesindeki her kayıtta
metin, göreli dosya adı, ses/hız ayarı, başlangıç/bitiş saniyeleri (`start`,
`end`), süre (`duration`), başlangıç/bitiş kareleri, önbellek bilgileri ve
`words` listesi yer alır. Zamanlar `narration.wav` dosyasının başlangıcına
göredir; bitiş anı aralığa dahil değildir. Tek bir cümle dosyasında çalışırken
kelime zamanlarından cümlenin `start` değerini çıkarın.

Cümle süreleri gerçek WAV karelerinden hesaplanır. Sessizlikler en yakın örnek
karesine yuvarlanır; toplam süre tam sayı karelerle tutulur. **Kelime zamanları
tahminidir; konuşmaya kesin hizalama yapılmaz.** Manifest bunu
`word_timing: "estimated_character_weight"` olarak belirtir. Süre, kelimelere
karakter sayıları oranında paylaştırılır; Çince/Japonca karakterler ayrı altyazı
birimleri sayılır. Motorun ürettiği ses içindeki sessizlikler de bu tahmine
dahildir. Yalnızca noktalama içeren parçalarda kelime listesi boştur.

Tüm sesler sıkıştırılmamış 16 bit PCM WAV olmalı; örnekleme hızları ve kanal
sayıları eşleşmelidir. Yeniden örnekleme yapılmaz. Farklı biçimlerde ses üreten
modeller arasında geçiş hata verir.

Ses üretimi ve biçim kontrolleri tamamlandıktan sonra çıktı dosyaları değiştirilir.
Bu aşamalardaki hata önceki çıktıyı korur; yeni önbellek kayıtları kalabilir.
Dosya değiştirme sırasında oluşan disk hatalarında tüm klasör için atomik işlem
garantisi yoktur. Önceki uzun bir çalışmadan kalan numaralı dosyalar silinmez;
güncel liste için manifesti kullanın veya yeni bir çıktı klasörü seçin. Aynı
klasöre eşzamanlı yazmayın. Ses doğrudan `narration.wav` dosyasına akış halinde
yazılır; bellekte yalnızca geçerli parça tutulur.

### Manifest örneği ve konsol çıktısı

`tts-batch render` komutu tamamlandığında tek satırlık bir özet basar:

```text
Rendered 2 segments (2.000s) to out/
```

Oluşan `out/manifest.json` dosyası cümle ve kelime zaman çizelgesini içerir:

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

## Seçenekler ve komut satırı

```sh
# Sentez yapmadan planlanan cümle parçalarını inceleme
tts-batch render examples/script.tr.md --dry-run

# Kurulu espeak seslerini listeleme
tts-batch --list-voices

# Özel ayarlarla seslendirme
tts-batch render script.md -o out/ --engine espeak --voice tr \
  --gap 0.15 --normalize rms --target-db -20
```

`--gap` saniye cinsindedir; varsayılanı 0.2'dir. `--normalize rms` her parçayı
varsayılan -20 dBFS RMS düzeyine yaklaştırır. `peak` tepe düzeyini hedefler;
`none` düzeyi korur. Hedef -120 ile 0 dBFS arasında olmalıdır. Kırpılmayı önleyen
kazanç sınırı nedeniyle RMS hedefine her zaman ulaşılamaz. Sessizlik değiştirilmez.
Bu işlem LUFS ölçümüne dayanan bir mastering işlemi değildir.

Ham motor çıktısı; motor kimliği, ses, hız ve metnin SHA-256 özetiyle önbelleğe
alınır. Yerel model/ses dosyalarının yolu, boyutu ve değişiklik zamanı da anahtara
girer. Kokoro'da dil, model ve yapılandırma bilgileri de kullanılır. Boşluk veya
normalizasyon değişirse ses yeniden üretilmez. `--cache-dir yol` ortak önbellek
seçer; `--no-cache` önbelleği kapatır. Bozuk kayıtlar yeniden oluşturulur. Modeli
aynı boyut ve zaman damgasıyla değiştirirseniz ya da motoru güncellerseniz
önbelleği elle temizleyin. Metinler, manifestler ve sesler yerel diskte kalır;
hassas içerik varsa bu dosyaları koruyun.

## İsteğe bağlı Kokoro

Bağımlılıkların desteklediği bir Python sürümüyle:

```sh
python -m pip install -e ".[kokoro]"
tts-batch render script.md -o out/ --engine kokoro \
  --kokoro-model models/kokoro-v1_0.pth \
  --kokoro-config models/config.json --voice voices/af_heart.pt --lang a
```

Model, yapılandırma ve `.pt` ses dosyası yerelde bulunmalıdır. `af_heart` gibi
yalnızca ses adı verilemez. Dil ve yazıdan foneme dönüşüm kaynaklarını önceden
hazırlayın; İngilizce için kurulu `en_core_web_sm` spaCy paketi gerekir. Adaptör,
Kokoro'yu içe aktarmadan önce `HF_HUB_OFFLINE=1` ve `TRANSFORMERS_OFFLINE=1`
ayarlarını yapar; bu ayarlar süreç boyunca kalır. Eksik kaynaklarda çevrim içi
modele geçmek yerine hata verir. Kesin ağ yalıtımı gerekiyorsa ağ erişimi kapalı
bir ortamda çalıştırın.

Desteklenen dil kodları: `a` ABD İngilizcesi, `b` Britanya İngilizcesi, `e`
İspanyolca, `f` Fransızca, `h` Hintçe, `i` İtalyanca, `p` Brezilya Portekizcesi ve
`z` Mandarin (v1.0 yapılandırması). İngilizce dışındaki dil bağımlılıkları ayrıca
hazırlanmalıdır. Japonca bağımlılığı kendiliğinden sözlük indirebildiğinden bu
adaptörde Japonca kapalıdır. Kokoro 0.9 API'si kullanılır; çıktı 24 kHz, tek
kanallıdır. Model lisanslarını ayrıca inceleyin.

## Geliştirme

Yeni motor, `name: str` ve `synth(text, voice, speed) -> bytes` arayüzünü
uygulayıp tam bir WAV dosyası döndürmelidir. İsteğe bağlı `cache_identity`
metni motor yapılandırmasını önbellek anahtarına ekleyebilir. Özel motorlar
Python'daki `tts_batch.render` fonksiyonuna nesne olarak verilebilir.

Depo kökünde:

```sh
python -m unittest discover -v
python -m pip install -e ".[dev]"
python -m ruff check .
python -m ruff format --check .
```

Testler motorları taklit eder ve sinüs dalgalarını kendisi üretir; model, ağ veya
motor kurulumu gerekmez. Geçici dosyalar Git'in yok saydığı `is/test-tmp/` altında
tutulur. CI, Ubuntu ve Windows üzerinde Python 3.10 ve 3.14 ile lint ve test
çalıştırır. İsteğe bağlı Kokoro bağımlılıkları ve gerçek model kalitesi CI
kapsamında değildir.

Proje: [YusufBeratZengin/tts-batch](https://github.com/YusufBeratZengin/tts-batch).
Lisans: [MIT](LICENSE).
