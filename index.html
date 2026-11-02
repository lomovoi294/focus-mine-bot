<!DOCTYPE html>
<html lang="ru">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">
    <title>Focus Mine</title>
    <!-- Подключаем скрипт Telegram Mini Apps -->
    <script src="https://telegram.org/js/telegram-web-app.js"></script>
    <style>
        body {
            margin: 0;
            padding: 0;
            background-color: #0d1117; /* Темный фон как в профиле */
            color: white;
            font-family: Arial, sans-serif;
            display: flex;
            flex-direction: column;
            align-items: center;
            justify-content: center;
            height: 100vh;
            overflow: hidden;
        }
        .circle-container {
            position: relative;
            width: 250px;
            height: 250px;
            display: flex;
            align-items: center;
            justify-content: center;
        }
        .circle {
            width: 100%;
            height: 100%;
            border-radius: 50%;
            background: radial-gradient(circle, #007bff 0%, #001a33 100%);
            box-shadow: 0 0 20px #007bff, 0 0 40px #007bff;
            transition: all 1s ease-in-out;
        }
        /* Анимация пульсации */
        .pulsing {
            animation: pulse 2s infinite alternate;
        }
        @keyframes pulse {
            0% { transform: scale(1); box-shadow: 0 0 20px #007bff, 0 0 40px #007bff; }
            100% { transform: scale(1.1); box-shadow: 0 0 40px #007bff, 0 0 80px #007bff; }
        }
        .timer {
            position: absolute;
            font-size: 40px;
            font-weight: bold;
            text-shadow: 0 0 10px rgba(255,255,255,0.5);
        }
        .status {
            margin-top: 30px;
            font-size: 18px;
            color: #8b949e;
            text-align: center;
            padding: 0 20px;
        }
        .btn {
            margin-top: 20px;
            padding: 15px 30px;
            font-size: 18px;
            color: white;
            background-color: #238636;
            border: none;
            border-radius: 10px;
            cursor: pointer;
            font-weight: bold;
            display: none; /* Скрыта по умолчанию */
        }
    </style>
</head>
<body>

    <div class="circle-container">
        <div id="circle" class="circle"></div>
        <div id="timer" class="timer">0.0s</div>
    </div>

    <div class="status" id="status">Нажми, чтобы начать майнинг</div>
    <button id="startBtn" class="btn" style="display: block;">Начать фокус</button>

    <script>
        const tg = window.Telegram.WebApp;
        tg.expand(); // Разворачиваем на весь экран

        let isMining = false;
        let timerInterval;
        let seconds = 0;
        
        const circle = document.getElementById('circle');
        const timerDisplay = document.getElementById('timer');
        const startBtn = document.getElementById('startBtn');
        const statusText = document.getElementById('status');

        // Функция запуска
        startBtn.addEventListener('click', () => {
            if (isMining) return;
            isMining = true;
            seconds = 0;
            
            circle.classList.add('pulsing');
            startBtn.style.display = 'none';
            statusText.innerText = "Майнинг идет... Не сворачивай!";
            
            timerInterval = setInterval(() => {
                seconds += 0.1;
                timerDisplay.innerText = seconds.toFixed(1) + 's';
            }, 100);
        });

        // Следим, не свернул ли пользователь приложение (ФОКУС)
        document.addEventListener("visibilitychange", () => {
            if (document.hidden && isMining) {
                // Пользователь ушел
clearInterval(timerInterval);
                isMining = false;
                circle.classList.remove('pulsing');
                statusText.innerText = "Фокус потерян! Свернул приложение.";
                startBtn.style.display = 'block';
                startBtn.innerText = "Попробовать снова";
            }
        });
    </script>
</body>
</html>
