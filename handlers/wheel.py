<!DOCTYPE html>
<html lang="uz">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Omad G'ildiragi</title>
    <script src="https://telegram.org"></script>
    <script src="https://adsgram.ai"></script>
    <style>
        body { font-family: sans-serif; text-align: center; background: #1a1a2e; color: #fff; padding: 15px; margin: 0; overflow-y: auto; }
        .main-wrapper { display: flex; flex-direction: column; align-items: center; justify-content: flex-start; min-height: 100vh; padding-bottom: 30px; }
        .wheel-container { position: relative; width: 280px; height: 280px; margin: 20px auto; }
        
        /* 12 ta teng sektor (har biri 30 darajadan) - Yutuq va Yutqazish navbatma-navbat */
        .wheel { width: 100%; height: 100%; border-radius: 50%; border: 5px solid #fff; background: conic-gradient(#ff2a5f 0deg 30deg, #333333 30deg 60deg, #ffb800 60deg 90deg, #333333 90deg 120deg, #00b8ff 120deg 150deg, #333333 150deg 180deg, #00ff66 180deg 210deg, #333333 210deg 240deg, #8a2be2 240deg 270deg, #333333 270deg 300deg, #ff6b6b 300deg 330deg, #333333 330deg 360deg); transition: transform 4s cubic-bezier(0.17, 0.67, 0.12, 0.99); position: relative; overflow: hidden; }
        .pointer { position: absolute; top: -15px; left: 50%; transform: translateX(-50%); width: 0; height: 0; border-left: 15px solid transparent; border-right: 15px solid transparent; border-top: 25px solid #fff; z-index: 10; }
        
        /* 12 ta sektor uchun matnlarni markazdan burchak bo'yicha aniq to'g'rilash */
        .label { position: absolute; width: 50%; height: 20px; top: 50%; left: 50%; transform-origin: 0% 50%; text-align: right; padding-right: 12px; box-sizing: border-box; font-weight: bold; font-size: 10px; text-shadow: 1px 1px 2px #000; line-height: 20px; }
        .l1 { transform: rotate(15deg) translate(-50%, -50%); }
        .l2 { transform: rotate(45deg) translate(-50%, -50%); color: #888; }
        .l3 { transform: rotate(75deg) translate(-50%, -50%); }
        .l4 { transform: rotate(105deg) translate(-50%, -50%); color: #888; }
        .l5 { transform: rotate(135deg) translate(-50%, -50%); }
        .l6 { transform: rotate(165deg) translate(-50%, -50%); color: #888; }
        .l7 { transform: rotate(195deg) translate(-50%, -50%); }
        .l8 { transform: rotate(225deg) translate(-50%, -50%); color: #888; }
        .l9 { transform: rotate(255deg) translate(-50%, -50%); }
        .l10 { transform: rotate(285deg) translate(-50%, -50%); color: #888; }
        .l11 { transform: rotate(315deg) translate(-50%, -50%); }
        .l12 { transform: rotate(345deg) translate(-50%, -50%); color: #888; }

        button { background: #ff2a5f; color: white; border: none; padding: 14px 20px; font-size: 16px; border-radius: 25px; cursor: pointer; margin-top: 15px; font-weight: bold; width: 85%; box-shadow: 0 4px 15px rgba(255, 42, 95, 0.4); z-index: 5; }
        button:disabled { background: #555; cursor: not-allowed; box-shadow: none; }
    </style>
</head>
<body>
    <div class="main-wrapper">
        <h2>🎡 OMAD G'ILDIRAGI 🎡</h2>
        <p style="font-size: 13px; margin: 5px 0;">Videoni ko'rib g'ildirakni aylantiring!</p>
        
        <div class="wheel-container">
            <div class="pointer"></div>
            <div class="wheel" id="wheel">
                <!-- Navbatma-navbat joylashgan aniq sektorlar matni -->
                <div class="label l1">1 EFC</div>
                <div class="label l2">0 BALANS</div>
                <div class="label l3">10 EFC</div>
                <div class="label l4">0 BALANS</div>
                <div class="label l5">50 EFC</div>
                <div class="label l6">0 BALANS</div>
                <div class="label l7">250 EFC</div>
                <div class="label l8">0 BALANS</div>
                <div class="label l9">130 COIN</div>
                <div class="label l10">0 BALANS</div>
                <div class="label l11">2000 COIN</div>
                <div class="label l12">0 BALANS</div>
            </div>
        </div>
        <button id="spinBtn" onclick="showAd()">📺 Video ko'rish va Aylantirish</button>
    </div>
    <script>
        const tg = window.Telegram.WebApp;
        tg.expand(); // Mini App oynasini telefon ekraniga to'liq yoyish

        // ⚠️ DIQQAT: "YOUR_BLOCK_ID_HERE" o'rniga AdsGram panelidan olgan block-id kodini yozing!
        const AdController = window.Adsgram.init({ blockId: "YOUR_BLOCK_ID_HERE" });

        function showAd() {
            document.getElementById("spinBtn").disabled = true;
            
            // AdsGram video reklamasini ishga tushirish
            AdController.show().then((result) => {
                // Video muvaffaqiyatli ko'rilsa, g'ildirak aylanadi
                startSpin();
            }).catch((error) => {
                alert("Reklama yuklanmadi yoki oxirigacha ko'rilmadi! Qayta urining.");
                document.getElementById("spinBtn").disabled = false;
            });
        }

        function startSpin() {
            const wheel = document.getElementById("wheel");
            // 12 ta sektorga mos ravishda tasodifiy burchak ostida kamida 4 marta aylantirish
            const randomDegrees = Math.floor(Math.random() * 360) + 1440; 
            wheel.style.transform = `rotate(${randomDegrees}deg)`;

            // G'ildirak aylanganda natija 4 soniyadan keyin botga ketadi
            setTimeout(() => {
                // Botga muvaffaqiyatli aylanganlik haqida signal yuborish
                tg.sendData(JSON.stringify({ action: "wheel_spin_success" }));
                // Mini App oynasini avtomat yopish
                tg.close();
            }, 4100);
        }
    </script>
</body>
</html>
