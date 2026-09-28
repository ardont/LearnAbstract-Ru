def render_student_portal() -> str:
    return """<!DOCTYPE html>
<html lang="ru">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Твой Путь · Кабинет Ученика & RAG Репетитор</title>
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
    <link href="https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;500;600;700;800&family=JetBrains+Mono:wght@400;500;600&display=swap" rel="stylesheet">
    <style>
        :root {
            --bg-base: #0b0f19;
            --bg-card: rgba(30, 41, 59, 0.7);
            --bg-card-hover: rgba(30, 41, 59, 0.9);
            --bg-input: rgba(15, 23, 42, 0.8);
            --border-color: rgba(255, 255, 255, 0.08);
            --border-glow: rgba(99, 102, 241, 0.3);
            --primary: #6366f1;
            --primary-light: #818cf8;
            --primary-glow: rgba(99, 102, 241, 0.25);
            --secondary: #06b6d4;
            --accent: #10b981;
            --danger: #ef4444;
            --warning: #f59e0b;
            --text-main: #f8fafc;
            --text-muted: #94a3b8;
            --radius-lg: 16px;
            --radius-md: 12px;
            --radius-sm: 8px;
        }

        * {
            box-sizing: border-box;
            margin: 0;
            padding: 0;
            font-family: 'Outfit', -apple-system, BlinkMacSystemFont, sans-serif;
        }

        body {
            background-color: var(--bg-base);
            background-image: 
                radial-gradient(at 0% 0%, rgba(99, 102, 241, 0.15) 0px, transparent 50%),
                radial-gradient(at 100% 0%, rgba(6, 182, 212, 0.12) 0px, transparent 50%),
                radial-gradient(at 50% 100%, rgba(16, 185, 129, 0.1) 0px, transparent 50%);
            background-attachment: fixed;
            color: var(--text-main);
            min-height: 100vh;
            display: flex;
            flex-direction: column;
        }

        /* Header */
        header {
            border-bottom: 1px solid var(--border-color);
            background: rgba(11, 15, 25, 0.85);
            backdrop-filter: blur(16px);
            position: sticky;
            top: 0;
            z-index: 100;
            padding: 14px 24px;
        }

        .header-inner {
            max-width: 1280px;
            margin: 0 auto;
            display: flex;
            align-items: center;
            justify-content: space-between;
            gap: 16px;
        }

        .brand {
            display: flex;
            align-items: center;
            gap: 12px;
            text-decoration: none;
            color: var(--text-main);
        }

        .brand-icon {
            width: 40px;
            height: 40px;
            background: linear-gradient(135deg, var(--primary), var(--secondary));
            border-radius: 10px;
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 20px;
            box-shadow: 0 4px 14px var(--primary-glow);
        }

        .brand-text h1 {
            font-size: 19px;
            font-weight: 700;
            letter-spacing: -0.02em;
            background: linear-gradient(to right, #fff, #94a3b8);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
        }

        .brand-text span {
            font-size: 12px;
            color: var(--secondary);
            font-weight: 500;
            display: block;
        }

        .nav-links {
            display: flex;
            gap: 8px;
            background: rgba(15, 23, 42, 0.6);
            padding: 4px;
            border-radius: 30px;
            border: 1px solid var(--border-color);
        }

        .nav-btn {
            background: transparent;
            border: none;
            color: var(--text-muted);
            padding: 8px 18px;
            border-radius: 20px;
            font-size: 14px;
            font-weight: 500;
            cursor: pointer;
            transition: all 0.2s;
        }

        .nav-btn.active {
            background: var(--primary);
            color: #fff;
            box-shadow: 0 2px 10px var(--primary-glow);
        }

        .header-actions {
            display: flex;
            align-items: center;
            gap: 16px;
        }

        .status-badge {
            display: flex;
            align-items: center;
            gap: 8px;
            font-size: 13px;
            color: #34d399;
            background: rgba(16, 185, 129, 0.1);
            border: 1px solid rgba(16, 185, 129, 0.3);
            padding: 6px 14px;
            border-radius: 20px;
        }

        .status-pulse {
            width: 8px;
            height: 8px;
            border-radius: 50%;
            background: #10b981;
            box-shadow: 0 0 10px #10b981;
        }

        .btn-teacher {
            background: rgba(255, 255, 255, 0.05);
            border: 1px solid var(--border-color);
            color: var(--text-main);
            padding: 8px 14px;
            border-radius: var(--radius-sm);
            font-size: 13px;
            text-decoration: none;
            transition: all 0.2s;
        }

        .btn-teacher:hover {
            background: rgba(255, 255, 255, 0.1);
            border-color: var(--text-muted);
        }

        /* Container */
        main {
            max-width: 1280px;
            width: 100%;
            margin: 24px auto;
            padding: 0 24px;
            flex: 1;
        }

        .tab-content {
            display: none;
        }

        .tab-content.active {
            display: block;
        }

        /* Chat Layout */
        .chat-container {
            display: grid;
            grid-template-columns: 320px 1fr;
            gap: 24px;
            height: calc(100vh - 150px);
            min-height: 600px;
        }

        /* Sidebar Settings */
        .chat-sidebar {
            background: var(--bg-card);
            backdrop-filter: blur(12px);
            border: 1px solid var(--border-color);
            border-radius: var(--radius-lg);
            padding: 20px;
            display: flex;
            flex-direction: column;
            gap: 20px;
        }

        .sidebar-title {
            font-size: 16px;
            font-weight: 600;
            color: var(--text-main);
            display: flex;
            align-items: center;
            gap: 8px;
        }

        .form-group {
            display: flex;
            flex-direction: column;
            gap: 8px;
        }

        .form-label {
            font-size: 13px;
            color: var(--text-muted);
            font-weight: 500;
        }

        .form-control {
            background: var(--bg-input);
            border: 1px solid var(--border-color);
            color: #fff;
            padding: 10px 14px;
            border-radius: var(--radius-sm);
            font-size: 14px;
            outline: none;
            transition: border-color 0.2s;
        }

        .form-control:focus {
            border-color: var(--primary);
        }

        .hobby-grid {
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 8px;
        }

        .hobby-card {
            background: var(--bg-input);
            border: 1px solid var(--border-color);
            padding: 10px;
            border-radius: var(--radius-sm);
            text-align: center;
            font-size: 13px;
            cursor: pointer;
            transition: all 0.2s;
            user-select: none;
        }

        .hobby-card:hover {
            border-color: var(--primary-light);
            background: rgba(99, 102, 241, 0.1);
        }

        .hobby-card.selected {
            background: rgba(99, 102, 241, 0.2);
            border-color: var(--primary);
            color: #fff;
            font-weight: 600;
            box-shadow: 0 0 12px var(--primary-glow);
        }

        .chip-list {
            display: flex;
            flex-direction: column;
            gap: 8px;
        }

        .chip-item {
            background: rgba(255, 255, 255, 0.03);
            border: 1px solid var(--border-color);
            border-radius: var(--radius-sm);
            padding: 8px 12px;
            font-size: 13px;
            color: var(--text-muted);
            cursor: pointer;
            transition: all 0.2s;
            text-align: left;
        }

        .chip-item:hover {
            background: rgba(99, 102, 241, 0.1);
            border-color: var(--primary);
            color: var(--text-main);
            transform: translateX(3px);
        }

        /* Chat Main Box */
        .chat-main {
            background: var(--bg-card);
            backdrop-filter: blur(12px);
            border: 1px solid var(--border-color);
            border-radius: var(--radius-lg);
            display: flex;
            flex-direction: column;
            overflow: hidden;
        }

        .chat-messages {
            flex: 1;
            padding: 24px;
            overflow-y: auto;
            display: flex;
            flex-direction: column;
            gap: 20px;
        }

        .message-bubble {
            max-width: 82%;
            display: flex;
            flex-direction: column;
            gap: 8px;
        }

        .message-user {
            align-self: flex-end;
        }

        .message-user .message-content {
            background: linear-gradient(135deg, var(--primary), #4f46e5);
            color: #fff;
            padding: 14px 18px;
            border-radius: 18px 18px 4px 18px;
            box-shadow: 0 4px 12px var(--primary-glow);
            font-size: 15px;
            line-height: 1.5;
        }

        .message-bot {
            align-self: flex-start;
        }

        .message-bot .message-header {
            display: flex;
            align-items: center;
            gap: 8px;
            font-size: 13px;
            color: var(--text-muted);
        }

        .message-bot .message-content {
            background: rgba(15, 23, 42, 0.9);
            border: 1px solid var(--border-color);
            color: var(--text-main);
            padding: 20px;
            border-radius: 18px 18px 18px 4px;
            font-size: 15px;
            line-height: 1.6;
            box-shadow: 0 4px 20px rgba(0, 0, 0, 0.2);
        }

        .badges-bar {
            display: flex;
            flex-wrap: wrap;
            gap: 8px;
            margin-bottom: 12px;
        }

        .badge {
            font-size: 12px;
            font-weight: 600;
            padding: 4px 10px;
            border-radius: 6px;
        }

        .badge-hobby {
            background: rgba(99, 102, 241, 0.2);
            color: #a5b4fc;
            border: 1px solid rgba(99, 102, 241, 0.3);
        }

        .badge-rag-active {
            background: rgba(16, 185, 129, 0.2);
            color: #34d399;
            border: 1px solid rgba(16, 185, 129, 0.4);
            font-weight: 700;
        }

        .badge-rag-idle {
            background: rgba(148, 163, 184, 0.12);
            color: #94a3b8;
            border: 1px solid rgba(148, 163, 184, 0.25);
        }

        .badge-speed {
            background: rgba(16, 185, 129, 0.15);
            color: #6ee7b7;
            border: 1px solid rgba(16, 185, 129, 0.3);
        }

        /* RAG Sources Accordion */
        .rag-sources-accordion {
            margin-top: 14px;
            background: rgba(15, 23, 42, 0.6);
            border: 1px solid rgba(16, 185, 129, 0.25);
            border-radius: var(--radius-sm);
            padding: 10px 14px;
            font-size: 13px;
        }

        .rag-sources-accordion summary {
            cursor: pointer;
            color: #6ee7b7;
            font-weight: 600;
            user-select: none;
            outline: none;
        }

        .rag-sources-accordion summary:hover {
            color: #34d399;
        }

        .rag-sources-body {
            margin-top: 10px;
            display: flex;
            flex-direction: column;
            gap: 10px;
            border-top: 1px dashed rgba(255, 255, 255, 0.1);
            padding-top: 10px;
        }

        .rag-chunk-item {
            background: rgba(30, 41, 59, 0.5);
            border-left: 3px solid #10b981;
            padding: 8px 12px;
            border-radius: 4px;
        }

        .rag-chunk-tag {
            font-size: 11px;
            font-weight: 700;
            color: #38bdf8;
            text-transform: uppercase;
            letter-spacing: 0.5px;
            display: block;
            margin-bottom: 4px;
        }

        .rag-chunk-item p {
            font-size: 12px;
            color: #cbd5e1;
            line-height: 1.5;
            margin: 0;
            white-space: pre-wrap;
        }

        /* Formula & code style inside messages */
        .formula-box {
            background: rgba(0, 0, 0, 0.4);
            border: 1px solid rgba(255, 255, 255, 0.1);
            padding: 6px 12px;
            border-radius: 8px;
            font-family: 'JetBrains Mono', monospace;
            font-size: 14px;
            color: #38bdf8;
            margin: 6px 0;
            display: inline-block;
        }

        /* Quiz Card inside message */
        .quiz-card {
            background: rgba(30, 41, 59, 0.8);
            border: 1px solid var(--border-glow);
            border-radius: var(--radius-md);
            padding: 16px;
            margin-top: 16px;
        }

        .quiz-title {
            font-size: 14px;
            font-weight: 600;
            color: #fbbf24;
            display: flex;
            align-items: center;
            gap: 6px;
            margin-bottom: 10px;
        }

        .quiz-question {
            font-size: 14px;
            color: #fff;
            margin-bottom: 12px;
            font-weight: 500;
        }

        .quiz-options {
            display: flex;
            flex-direction: column;
            gap: 8px;
        }

        .quiz-opt-btn {
            background: rgba(15, 23, 42, 0.7);
            border: 1px solid var(--border-color);
            color: var(--text-main);
            padding: 10px 14px;
            border-radius: var(--radius-sm);
            cursor: pointer;
            font-size: 13px;
            text-align: left;
            transition: all 0.2s;
        }

        .quiz-opt-btn:hover {
            border-color: var(--primary);
            background: rgba(99, 102, 241, 0.15);
        }

        .quiz-opt-btn.correct {
            background: rgba(16, 185, 129, 0.25) !important;
            border-color: #10b981 !important;
            color: #6ee7b7 !important;
        }

        .quiz-opt-btn.wrong {
            background: rgba(239, 68, 68, 0.25) !important;
            border-color: #ef4444 !important;
            color: #fca5a5 !important;
        }

        .quiz-feedback {
            margin-top: 10px;
            font-size: 13px;
            font-weight: 600;
        }

        /* Chat Input Bar */
        .chat-input-bar {
            padding: 16px 20px;
            border-top: 1px solid var(--border-color);
            background: rgba(15, 23, 42, 0.8);
            display: flex;
            align-items: center;
            gap: 12px;
        }

        .chat-input {
            flex: 1;
            background: rgba(30, 41, 59, 0.6);
            border: 1px solid var(--border-color);
            color: #fff;
            padding: 12px 18px;
            border-radius: 24px;
            font-size: 15px;
            outline: none;
            transition: all 0.2s;
        }

        .chat-input:focus {
            border-color: var(--primary);
            box-shadow: 0 0 0 3px var(--primary-glow);
        }

        .btn-send {
            background: linear-gradient(135deg, var(--primary), var(--secondary));
            color: #fff;
            border: none;
            width: 44px;
            height: 44px;
            border-radius: 50%;
            display: flex;
            align-items: center;
            justify-content: center;
            cursor: pointer;
            transition: all 0.2s;
            box-shadow: 0 4px 14px var(--primary-glow);
        }

        .btn-send:hover {
            transform: scale(1.05);
        }

        .btn-send:disabled {
            opacity: 0.5;
            cursor: not-allowed;
            transform: none;
        }

        /* Upload Tab */
        .upload-layout {
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 24px;
        }

        .card {
            background: var(--bg-card);
            backdrop-filter: blur(12px);
            border: 1px solid var(--border-color);
            border-radius: var(--radius-lg);
            padding: 24px;
        }

        .card-header {
            margin-bottom: 20px;
        }

        .card-header h2 {
            font-size: 18px;
            font-weight: 700;
            color: #fff;
            margin-bottom: 6px;
        }

        .card-header p {
            font-size: 14px;
            color: var(--text-muted);
        }

        .dropzone {
            border: 2px dashed rgba(99, 102, 241, 0.4);
            border-radius: var(--radius-md);
            padding: 40px 20px;
            text-align: center;
            background: rgba(15, 23, 42, 0.4);
            cursor: pointer;
            transition: all 0.2s;
            margin-bottom: 20px;
        }

        .dropzone:hover, .dropzone.dragover {
            border-color: var(--secondary);
            background: rgba(6, 182, 212, 0.08);
        }

        .dropzone-icon {
            font-size: 40px;
            margin-bottom: 12px;
            color: var(--primary-light);
        }

        .dropzone-text {
            font-size: 15px;
            font-weight: 500;
            color: #fff;
            margin-bottom: 4px;
        }

        .dropzone-sub {
            font-size: 13px;
            color: var(--text-muted);
        }

        .btn-primary {
            background: linear-gradient(135deg, var(--primary), #4f46e5);
            color: #fff;
            border: none;
            padding: 12px 24px;
            border-radius: var(--radius-sm);
            font-size: 15px;
            font-weight: 600;
            cursor: pointer;
            width: 100%;
            transition: all 0.2s;
            box-shadow: 0 4px 14px var(--primary-glow);
        }

        .btn-primary:hover {
            opacity: 0.95;
            transform: translateY(-1px);
        }

        .btn-primary:disabled {
            opacity: 0.5;
            cursor: not-allowed;
            transform: none;
        }

        /* Books Table */
        .table-responsive {
            overflow-x: auto;
        }

        table {
            width: 100%;
            border-collapse: collapse;
            font-size: 14px;
        }

        th {
            text-align: left;
            padding: 12px 14px;
            color: var(--text-muted);
            border-bottom: 1px solid var(--border-color);
            font-weight: 600;
        }

        td {
            padding: 14px;
            border-bottom: 1px solid rgba(255, 255, 255, 0.05);
            color: var(--text-main);
        }

        /* Bot Tab */
        .bot-card-wrapper {
            max-width: 680px;
            margin: 40px auto;
            background: var(--bg-card);
            border: 1px solid var(--border-glow);
            border-radius: 24px;
            padding: 36px;
            text-align: center;
            box-shadow: 0 10px 40px rgba(0, 0, 0, 0.4);
        }

        .bot-avatar {
            width: 88px;
            height: 88px;
            border-radius: 50%;
            margin: 0 auto 20px;
            border: 3px solid var(--primary);
            box-shadow: 0 0 20px var(--primary-glow);
            display: block;
        }

        .btn-max-launch {
            display: inline-flex;
            align-items: center;
            gap: 10px;
            background: linear-gradient(135deg, #0ea5e9, #6366f1);
            color: #fff;
            text-decoration: none;
            padding: 14px 28px;
            border-radius: 30px;
            font-size: 16px;
            font-weight: 700;
            margin: 20px 0;
            box-shadow: 0 6px 20px rgba(14, 165, 233, 0.4);
            transition: all 0.2s;
        }

        .btn-max-launch:hover {
            transform: scale(1.05);
            box-shadow: 0 8px 25px rgba(14, 165, 233, 0.6);
        }

        .steps-box {
            text-align: left;
            background: rgba(15, 23, 42, 0.6);
            border-radius: var(--radius-md);
            padding: 20px;
            margin-top: 24px;
        }

        .step-item {
            display: flex;
            align-items: flex-start;
            gap: 12px;
            margin-bottom: 12px;
            font-size: 14px;
            color: var(--text-muted);
        }

        .step-item:last-child {
            margin-bottom: 0;
        }

        .step-num {
            background: var(--primary);
            color: #fff;
            width: 22px;
            height: 22px;
            border-radius: 50%;
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 12px;
            font-weight: 700;
            flex-shrink: 0;
        }

        @media (max-width: 900px) {
            .chat-container {
                grid-template-columns: 1fr;
                height: auto;
            }
            .chat-sidebar {
                order: 2;
            }
            .upload-layout {
                grid-template-columns: 1fr;
            }
        }
    </style>
</head>
<body>

    <header>
        <div class="header-inner">
            <a href="/student" class="brand">
                <div class="brand-icon">🎓</div>
                <div class="brand-text">
                    <h1>Твой Путь</h1>
                    <span>Абстрактный Репетитор</span>
                </div>
            </a>

            <div class="nav-links">
                <button class="nav-btn active" onclick="switchTab('chat')">💬 Чат Репетитора</button>
                <button class="nav-btn" onclick="switchTab('rag')">📚 Загрузка в RAG</button>
                <button class="nav-btn" onclick="switchTab('max')">🤖 Бот в MAX</button>
            </div>

            <div class="header-actions">
                <div class="status-badge">
                    <div class="status-pulse"></div>
                    <span>Онлайн (Tailscale)</span>
                </div>
                <a href="/teacher" target="_blank" class="btn-teacher">Панель Учителя ↗</a>
            </div>
        </div>
    </header>

    <main>
        <!-- TAB 1: ЧАТ -->
        <div id="tab-chat" class="tab-content active">
            <div class="chat-container">
                <!-- Sidebar -->
                <div class="chat-sidebar">
                    <div class="sidebar-title">⚙️ Персонализация</div>

                    <div class="form-group">
                        <label class="form-label">Имя или ID Ученика</label>
                        <input type="text" id="studentId" class="form-control" value="student_demo">
                    </div>

                    <div class="form-group">
                        <label class="form-label">Класс</label>
                        <select id="studentGrade" class="form-control">
                            <option value="7" selected>7 класс</option>
                            <option value="8">8 класс</option>
                            <option value="9">9 класс</option>
                            <option value="10">10 класс</option>
                            <option value="11">11 класс</option>
                        </select>
                    </div>

                    <div class="form-group">
                        <label class="form-label">Любимое увлечение (Хобби)</label>
                        <div class="hobby-grid">
                            <div class="hobby-card selected" onclick="selectHobby('Футбол', this)">⚽ Футбол</div>
                            <div class="hobby-card" onclick="selectHobby('Видеоигры', this)">🎮 Игры</div>
                            <div class="hobby-card" onclick="selectHobby('Музыка', this)">🎵 Музыка</div>
                            <div class="hobby-card" onclick="selectHobby('Космос', this)">🚀 Космос</div>
                            <div class="hobby-card" onclick="selectHobby('Кино', this)">🎬 Кино</div>
                            <div class="hobby-card" onclick="selectHobby('Общий', this)">🌐 Кругозор</div>
                        </div>
                    </div>

                    <div class="form-group">
                        <label class="form-label">Быстрые вопросы для демо:</label>
                        <div class="chip-list">
                            <button class="chip-item" onclick="askPreset('Объясни теорему Пифагора')">📐 Теорема Пифагора</button>
                            <button class="chip-item" onclick="askPreset('Объясни квадратные уравнения')">⚡ Квадратные уравнения</button>
                            <button class="chip-item" onclick="askPreset('Что такое Закон Ома?')">🔌 Закон Ома</button>
                            <button class="chip-item" onclick="askPreset('Как работает сила гравитации?')">🪐 Гравитация</button>
                        </div>
                    </div>
                </div>

                <!-- Chat Box -->
                <div class="chat-main">
                    <div class="chat-messages" id="chatMessages">
                        <div class="message-bubble message-bot">
                            <div class="message-header">🤖 Абстрактный Репетитор</div>
                            <div class="message-content">
                                Привет! Я объясняю сложные школьные формулы и законы через твои реальные интересы (спорт, игры, музыку).
                                Выбери своё хобби слева и задай любой вопрос, например: <strong>«Объясни квадратные уравнения»</strong>!
                            </div>
                        </div>
                    </div>

                    <div class="chat-input-bar">
                        <input type="text" id="userInput" class="chat-input" placeholder="Задай школьный вопрос (например, «Объясни квадратные уравнения»)..." onkeydown="if(event.key==='Enter') sendMessage()">
                        <button id="sendBtn" class="btn-send" onclick="sendMessage()">➤</button>
                    </div>
                </div>
            </div>
        </div>

        <!-- TAB 2: ЗАГРУЗКА В RAG -->
        <div id="tab-rag" class="tab-content">
            <div class="upload-layout">
                <div class="card">
                    <div class="card-header">
                        <h2>📚 Загрузка учебника в векторную базу</h2>
                        <p>Загрузите реальный школьный учебник в формате PDF. Система автоматически извлечёт текст, разобьёт на чанки и добавит в RAG-индекс.</p>
                    </div>

                    <div class="form-group" style="margin-bottom: 16px;">
                        <label class="form-label">Предмет</label>
                        <select id="uploadSubject" class="form-control">
                            <option value="algebra" selected>Алгебра (algebra)</option>
                            <option value="physics">Физика (physics)</option>
                            <option value="cs">Информатика (cs)</option>
                            <option value="biology">Биология (biology)</option>
                        </select>
                    </div>

                    <div class="dropzone" id="dropzone" onclick="document.getElementById('fileInput').click()">
                        <div class="dropzone-icon">📄</div>
                        <div class="dropzone-text" id="dropzoneText">Нажмите для выбора PDF файла или перетащите сюда</div>
                        <div class="dropzone-sub">Поддерживаются стандартные PDF с текстовым слоем</div>
                        <input type="file" id="fileInput" accept=".pdf" style="display:none;" onchange="handleFileSelected(this.files)">
                    </div>

                    <button id="btnUpload" class="btn-primary" onclick="uploadTextbook()" disabled>Загрузить и проиндексировать в RAG</button>

                    <div id="uploadStatus" style="margin-top: 16px; display: none;"></div>
                </div>

                <div class="card">
                    <div class="card-header">
                        <h2>📖 Активные учебники в RAG</h2>
                        <p>Список проиндексированных пособий, по которым ИИ-репетитор проверяет факты и генерирует формулы.</p>
                    </div>

                    <div class="table-responsive">
                        <table>
                            <thead>
                                <tr>
                                    <th>Предмет</th>
                                    <th>Файл / Источник</th>
                                    <th>Чанков в базе</th>
                                    <th>Статус</th>
                                </tr>
                            </thead>
                            <tbody id="textbooksTableBody">
                                <tr><td colspan="4" style="text-align:center; color:var(--text-muted);">Загрузка списка учебников...</td></tr>
                            </tbody>
                        </table>
                    </div>
                </div>
            </div>
        </div>

        <!-- TAB 3: MAX BOT -->
        <div id="tab-max" class="tab-content">
            <div class="bot-card-wrapper">
                <img src="https://i.oneme.ru/i?r=BTFjO43w8Yr1OSJ4tcurq5HiNumsXLY3PqE_FARjsJ6TmDoNQZaVUyFC4Sn0-ZqEC6E" class="bot-avatar" alt="MAX Bot Avatar">
                <h2 style="font-size: 24px; font-weight: 800; margin-bottom: 6px;">@t569_hakaton_max_bot</h2>
                <p style="color: var(--secondary); font-weight: 500; margin-bottom: 12px;">Официальный бот «Твой Путь: Абстрактный Репетитор»</p>
                <p style="color: var(--text-muted); font-size: 15px; line-height: 1.5;">
                    Бот работает на базе мессенджера <strong>MAX</strong>, подключён к шине Apache Kafka и отвечает за 150–300 мс с поддержкой формул, инлайн-квизов и таймера Watchdog.
                </p>

                <a href="https://max.ru/t569_hakaton_max_bot" target="_blank" class="btn-max-launch">
                    <span>🚀 Открыть бота в MAX</span>
                </a>

                <div class="steps-box">
                    <h3 style="font-size: 15px; margin-bottom: 14px; color: #fff;">📱 5 простых шагов для теста в мессенджере:</h3>
                    <div class="step-item">
                        <div class="step-num">1</div>
                        <div>Откройте приложение MAX на телефоне или ПК и найдите бота <code>@t569_hakaton_max_bot</code>.</div>
                    </div>
                    <div class="step-item">
                        <div class="step-num">2</div>
                        <div>Нажмите <strong>/start</strong>.</div>
                    </div>
                    <div class="step-item">
                        <div class="step-num">3</div>
                        <div>Нажмите <strong>«Согласен»</strong> (для 152-ФЗ сохранения прогресса).</div>
                    </div>
                    <div class="step-item">
                        <div class="step-num">4</div>
                        <div>Выберите увлечение: например, <strong>«Футбол ⚽»</strong> или <strong>«Видеоигры 🎮»</strong>.</div>
                    </div>
                    <div class="step-item">
                        <div class="step-num">5</div>
                        <div>Напишите вопрос: <strong>«Объясни квадратные уравнения»</strong> и пройдите интерактивный микро-тест!</div>
                    </div>
                </div>
            </div>
        </div>
    </main>

    <script>
        let currentHobby = 'Футбол';
        let selectedFile = null;

        function switchTab(tabName) {
            document.querySelectorAll('.nav-btn').forEach(btn => btn.classList.remove('active'));
            document.querySelectorAll('.tab-content').forEach(tab => tab.classList.remove('active'));

            if (tabName === 'chat') {
                document.querySelectorAll('.nav-btn')[0].classList.add('active');
                document.getElementById('tab-chat').classList.add('active');
            } else if (tabName === 'rag') {
                document.querySelectorAll('.nav-btn')[1].classList.add('active');
                document.getElementById('tab-rag').classList.add('active');
                loadTextbooksList();
            } else if (tabName === 'max') {
                document.querySelectorAll('.nav-btn')[2].classList.add('active');
                document.getElementById('tab-max').classList.add('active');
            }
        }

        function selectHobby(hobby, el) {
            currentHobby = hobby;
            document.querySelectorAll('.hobby-card').forEach(c => c.classList.remove('selected'));
            el.classList.add('selected');
        }

        function askPreset(text) {
            document.getElementById('userInput').value = text;
            sendMessage();
        }

        async function sendMessage() {
            const input = document.getElementById('userInput');
            const query = input.value.trim();
            if (!query) return;

            const studentId = document.getElementById('studentId').value || 'student_demo';
            const grade = parseInt(document.getElementById('studentGrade').value) || 7;
            const messagesContainer = document.getElementById('chatMessages');

            // 1. Append User Message
            const userMsg = document.createElement('div');
            userMsg.className = 'message-bubble message-user';
            userMsg.innerHTML = `<div class="message-content">${escapeHtml(query)}</div>`;
            messagesContainer.appendChild(userMsg);
            input.value = '';
            messagesContainer.scrollTop = messagesContainer.scrollHeight;

            // 2. Append Loading Placeholder
            const loadingMsg = document.createElement('div');
            loadingMsg.className = 'message-bubble message-bot';
            loadingMsg.id = 'loadingBubble';
            loadingMsg.innerHTML = `
                <div class="message-header">🤖 Репетитор подбирает аналогию...</div>
                <div class="message-content" style="color:var(--text-muted);">
                    ⚡ Поиск в RAG и генерация метафоры через ${currentHobby}...
                </div>
            `;
            messagesContainer.appendChild(loadingMsg);
            messagesContainer.scrollTop = messagesContainer.scrollHeight;

            const sendBtn = document.getElementById('sendBtn');
            sendBtn.disabled = true;

            try {
                const resp = await fetch('/api/student/ask', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        user_id: studentId,
                        topic: query,
                        interest: currentHobby,
                        grade: grade
                    })
                });

                const data = await resp.json();
                const bubble = document.getElementById('loadingBubble');
                if (bubble) bubble.remove();

                if (data.status === 'rate_limited') {
                    appendBotMessage(data.message, '⚠️ Лимит запросов', 'badge-speed');
                    return;
                }

                // Append Bot Response
                renderBotExplanation(data, query);

            } catch (err) {
                console.error(err);
                const bubble = document.getElementById('loadingBubble');
                if (bubble) bubble.remove();
                appendBotMessage('Произошла ошибка связи с сервером. Попробуйте еще раз.', 'Ошибка', 'badge-speed');
            } finally {
                sendBtn.disabled = false;
                messagesContainer.scrollTop = messagesContainer.scrollHeight;
            }
        }

        function renderBotExplanation(data, originalQuery) {
            const container = document.getElementById('chatMessages');
            const botMsg = document.createElement('div');
            botMsg.className = 'message-bubble message-bot';

            const sourceText = data.source ? data.source.replace('_', ' ').toUpperCase() : 'FALLBACK';
            const latency = data.latency_ms || 180;
            const ragHits = data.rag_hits || (data.rag_chunks ? data.rag_chunks.length : 0);

            // Бейдж RAG: зеленый если найден контекст, серый если не найден
            let ragBadgeHtml = '';
            if (ragHits > 0) {
                ragBadgeHtml = `<span class="badge badge-rag-active" title="Извлечено ${ragHits} релевантных фрагментов из учебника">🟢 📚 RAG: ${ragHits} чанка из учебника</span>`;
            } else {
                ragBadgeHtml = `<span class="badge badge-rag-idle" title="Контекст не найден в загруженных учебниках">⚪ 📚 RAG: не использован</span>`;
            }

            // Аккордеон с цитатами из учебника
            let ragDetailsHtml = '';
            if (data.rag_chunks && data.rag_chunks.length > 0) {
                ragDetailsHtml = `
                    <details class="rag-sources-accordion">
                        <summary>📖 Показать цитаты из учебника (${data.rag_chunks.length} фрагмента)</summary>
                        <div class="rag-sources-body">
                            ${data.rag_chunks.map((c, i) => `
                                <div class="rag-chunk-item">
                                    <span class="rag-chunk-tag">Цитата #${i + 1} (${escapeHtml(data.rag_subject || 'Учебник')})</span>
                                    <p>${escapeHtml(c)}</p>
                                </div>
                            `).join('')}
                        </div>
                    </details>
                `;
            }

            let quizHtml = '';
            if (data.quiz && data.quiz.options && data.quiz.options.length > 0) {
                const quizId = data.quiz.quiz_id;
                const optionsBtns = data.quiz.options.map((opt, idx) => `
                    <button class="quiz-opt-btn" onclick="submitQuizAnswer('${quizId}', ${idx}, this)">
                        ${String.fromCharCode(65 + idx)}) ${escapeHtml(opt)}
                    </button>
                `).join('');

                quizHtml = `
                    <div class="quiz-card" id="quiz-${quizId}">
                        <div class="quiz-title">🎯 Проверь себя (Микро-тест)</div>
                        <div class="quiz-question">${escapeHtml(data.quiz.question)}</div>
                        <div class="quiz-options">${optionsBtns}</div>
                        <div class="quiz-feedback" id="feedback-${quizId}" style="display:none;"></div>
                    </div>
                `;
            }

            botMsg.innerHTML = `
                <div class="message-header">🤖 Абстрактный Репетитор</div>
                <div class="message-content">
                    <div class="badges-bar">
                        <span class="badge badge-hobby">🎯 Аналогия: ${escapeHtml(currentHobby)}</span>
                        ${ragBadgeHtml}
                        <span class="badge badge-speed">⚡ ${latency} мс (${sourceText})</span>
                    </div>
                    <div style="white-space: pre-wrap;">${formatExplanation(data.explanation)}</div>
                    ${ragDetailsHtml}
                    ${quizHtml}
                </div>
            `;

            container.appendChild(botMsg);
            container.scrollTop = container.scrollHeight;
        }

        async function submitQuizAnswer(quizId, optionIndex, btnElement) {
            const card = document.getElementById(`quiz-${quizId}`);
            const feedback = document.getElementById(`feedback-${quizId}`);
            const studentId = document.getElementById('studentId').value || 'student_demo';

            // Disable all buttons in this quiz
            card.querySelectorAll('.quiz-opt-btn').forEach(b => b.disabled = true);

            try {
                const resp = await fetch('/api/student/quiz_answer', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        max_user_id: studentId,
                        quiz_id: quizId,
                        selected_option_index: optionIndex
                    })
                });

                const res = await resp.json();
                feedback.style.display = 'block';

                if (res.status === 'correct') {
                    btnElement.classList.add('correct');
                    feedback.style.color = '#34d399';
                    feedback.innerHTML = '🎉 ' + (res.message || 'Отлично! Ответ абсолютно верен (+10 очков)!');
                } else if (res.status === 'wrong') {
                    btnElement.classList.add('wrong');
                    feedback.style.color = '#f87171';
                    feedback.innerHTML = '❌ ' + (res.message || 'Не совсем точно. Попробуй перечитать аналогию!');
                } else {
                    feedback.style.color = '#fbbf24';
                    feedback.innerHTML = 'ℹ️ ' + (res.message || 'Тест уже сдан.');
                }
            } catch (err) {
                console.error(err);
                feedback.style.display = 'block';
                feedback.style.color = '#f87171';
                feedback.innerHTML = 'Ошибка отправки ответа на проверку.';
            }
        }

        function formatExplanation(text) {
            if (!text) return '';
            let formatted = escapeHtml(text);
            // Replace formulas like x^2 with <code>
            formatted = formatted.replace(/([a-zA-Z0-9_]+[\^²³][a-zA-Z0-9_]*)/g, '<span class="formula-box">$1</span>');
            return formatted;
        }

        function escapeHtml(str) {
            return (str || '').replace(/[&<>"']/g, function(m) {
                return {'&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;'}[m];
            });
        }

        function appendBotMessage(text, badgeText, badgeClass) {
            const container = document.getElementById('chatMessages');
            const botMsg = document.createElement('div');
            botMsg.className = 'message-bubble message-bot';
            botMsg.innerHTML = `
                <div class="message-header">🤖 Абстрактный Репетитор</div>
                <div class="message-content">
                    <div class="badges-bar"><span class="badge ${badgeClass}">${badgeText}</span></div>
                    <div>${escapeHtml(text)}</div>
                </div>
            `;
            container.appendChild(botMsg);
            container.scrollTop = container.scrollHeight;
        }

        // Upload Logic
        function handleFileSelected(files) {
            if (!files || files.length === 0) return;
            selectedFile = files[0];
            const sizeKb = (selectedFile.size / 1024).toFixed(1);
            document.getElementById('dropzoneText').innerHTML = `✅ <strong>Выбран файл:</strong> ${escapeHtml(selectedFile.name)} (${sizeKb} КБ)`;
            const btn = document.getElementById('btnUpload');
            btn.disabled = false;
            btn.innerHTML = `🚀 Нажмите сюда, чтобы загрузить «${escapeHtml(selectedFile.name)}»`;
            btn.style.boxShadow = '0 0 20px rgba(99, 102, 241, 0.8)';
            btn.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
        }

        // Drag & Drop
        const dropzone = document.getElementById('dropzone');
        ['dragenter', 'dragover'].forEach(eventName => {
            dropzone.addEventListener(eventName, (e) => { e.preventDefault(); dropzone.classList.add('dragover'); }, false);
        });
        ['dragleave', 'drop'].forEach(eventName => {
            dropzone.addEventListener(eventName, (e) => { e.preventDefault(); dropzone.classList.remove('dragover'); }, false);
        });
        dropzone.addEventListener('drop', (e) => {
            const dt = e.dataTransfer;
            const files = dt.files;
            handleFileSelected(files);
        });

        async function uploadTextbook() {
            if (!selectedFile) return;

            const btn = document.getElementById('btnUpload');
            const statusBox = document.getElementById('uploadStatus');
            const subject = document.getElementById('uploadSubject').value;

            btn.disabled = true;
            btn.innerText = '⏳ Индексация учебника...';
            statusBox.style.display = 'block';
            statusBox.innerHTML = '<span style="color:#67e8f9;">Обработка PDF, извлечение текстового слоя и генерация чанков...</span>';

            const formData = new FormData();
            formData.append('file', selectedFile);
            formData.append('subject', subject);

            try {
                const resp = await fetch('/api/student/upload_textbook', {
                    method: 'POST',
                    body: formData
                });

                const res = await resp.json();
                if (res.status === 'ok') {
                    statusBox.innerHTML = `
                        <div style="background:rgba(16,185,129,0.15); border:1px solid #10b981; padding:12px; border-radius:8px; color:#6ee7b7;">
                            ✅ ${res.message}<br>
                            <strong>Извлечено чанков:</strong> ${res.chunks_count} | <strong>Предмет:</strong> ${res.subject}
                        </div>
                    `;
                    loadTextbooksList();
                } else {
                    statusBox.innerHTML = `
                        <div style="background:rgba(239,68,68,0.15); border:1px solid #ef4444; padding:12px; border-radius:8px; color:#fca5a5;">
                            ❌ ${res.message}
                        </div>
                    `;
                }
            } catch (err) {
                console.error(err);
                statusBox.innerHTML = `
                    <div style="background:rgba(239,68,68,0.15); border:1px solid #ef4444; padding:12px; border-radius:8px; color:#fca5a5;">
                        ❌ Ошибка загрузки файла на сервер.
                    </div>
                `;
            } finally {
                btn.disabled = false;
                btn.innerText = 'Загрузить и проиндексировать в RAG';
            }
        }

        async function loadTextbooksList() {
            const tbody = document.getElementById('textbooksTableBody');
            try {
                const resp = await fetch('/api/student/textbooks');
                const data = await resp.json();

                if (!data.textbooks || data.textbooks.length === 0) {
                    tbody.innerHTML = '<tr><td colspan="4" style="text-align:center; color:var(--text-muted);">В базе пока нет проиндексированных учебников. Загрузите первый!</td></tr>';
                    return;
                }

                tbody.innerHTML = data.textbooks.map(tb => `
                    <tr>
                        <td><strong>${escapeHtml(tb.subject.toUpperCase())}</strong></td>
                        <td>${tb.sources ? tb.sources.map(s => escapeHtml(s)).join(', ') : 'Учебник'}</td>
                        <td><span style="font-family:'JetBrains Mono',monospace; color:#38bdf8; font-weight:700;">${tb.chunks_count} чанков</span></td>
                        <td><span style="color:#34d399; font-weight:600;">● Готов к поиску</span></td>
                    </tr>
                `).join('');
            } catch (e) {
                console.error(e);
                tbody.innerHTML = '<tr><td colspan="4" style="text-align:center; color:var(--danger);">Не удалось загрузить список учебников.</td></tr>';
            }
        }

        // Init
        document.addEventListener('DOMContentLoaded', () => {
            loadTextbooksList();
        });
    </script>
</body>
</html>
"""
