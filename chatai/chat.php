<?php
header('Content-Type: application/json; charset=utf-8');
header('Access-Control-Allow-Origin: *');
header('Access-Control-Allow-Headers: Content-Type');

if ($_SERVER['REQUEST_METHOD'] === 'OPTIONS') {
    exit;
}

const API_KEY       = 'ISI_API_KEY_KAMU';
const MODEL         = 'gemini-3.5-flash';
const MAKS_KARAKTER = 500;

function kirimJson($data, $kode = 200) {
    http_response_code($kode);
    echo json_encode($data);
    exit;
}

function panggilGemini($payload) {
    $url = 'https://generativelanguage.googleapis.com/v1beta/models/'
         . MODEL . ':generateContent';

    $ch = curl_init($url);
    curl_setopt_array($ch, [
        CURLOPT_POST           => true,
        CURLOPT_POSTFIELDS     => json_encode($payload),
        CURLOPT_RETURNTRANSFER => true,
        CURLOPT_TIMEOUT        => 30,
        CURLOPT_SSL_VERIFYPEER => false, // khusus localhost
        CURLOPT_HTTPHEADER     => [
            'Content-Type: application/json',
            'x-goog-api-key: ' . API_KEY
        ]
    ]);
    $hasil = curl_exec($ch);
    $kode  = curl_getinfo($ch, CURLINFO_HTTP_CODE);
    curl_close($ch);

    return [$hasil, $kode];
}

// Endpoint 1: GET chat.php?cek=1 (cek status server)
if (isset($_GET['cek'])) {
    kirimJson([
        'online'       => true,
        'model'        => MODEL,
        'kunci_terisi' => (API_KEY !== 'ISI_API_KEY_KAMU')
    ]);
}

// Endpoint 2: POST chat.php (kirim pertanyaan)
$masuk = json_decode(file_get_contents('php://input'), true);
$pesan = trim($masuk['pesan'] ?? '');

if ($pesan === '') {
    kirimJson(['pesan_error' => 'Tulis dulu pertanyaannya ya.'], 400);
}
if (mb_strlen($pesan) > MAKS_KARAKTER) {
    kirimJson(['pesan_error' => 'Pertanyaan kepanjangan (maks ' . MAKS_KARAKTER . ' karakter).'], 400);
}

$peran = 'Kamu pemandu kuliner khas Semarang. Jawab dalam bahasa Indonesia, '
       . 'ramah, maksimal 5 poin, tanpa format markdown atau tanda bintang.';

$payload = [
    'system_instruction' => ['parts' => [['text' => $peran]]],
    'contents'           => [['parts' => [['text' => $pesan]]]]
];

$t0 = microtime(true);
[$hasil, $kode] = panggilGemini($payload);
$durasi = round((microtime(true) - $t0) * 1000);

if ($hasil === false) {
    kirimJson(['pesan_error' => 'Server gagal menghubungi Gemini API. Cek koneksi internet.'], 502);
}

$data = json_decode($hasil, true);

if ($kode !== 200) {
    $alasan = $data['error']['message'] ?? '-';
    kirimJson(['pesan_error' => "Gemini API menolak permintaan ($kode): $alasan"], 502);
}

$teks = $data['candidates'][0]['content']['parts'][0]['text'] ?? null;
if ($teks === null) {
    kirimJson(['pesan_error' => 'Gemini API tidak memberi balasan. Coba kalimat lain.'], 502);
}

kirimJson([
    'balasan' => $teks,
    'info'    => ['model' => MODEL, 'durasi_ms' => $durasi]
]);
