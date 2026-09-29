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
            --bg-input: rgba(15, 23, 42, 0.85);
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

        [data-theme="light"] {
            --bg-base: #f1f5f9;
            --bg-card: rgba(255, 255, 255, 0.92);
            --bg-card-hover: #ffffff;
            --bg-input: #ffffff;
            --border-color: rgba(0, 0, 0, 0.1);
            --border-glow: rgba(99, 102, 241, 0.2);
            --text-main: #0f172a;
            --text-muted: #64748b;
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
                radial-gradient(at 50% 100%, rgba(16, 185, 129, 0.08) 0px, transparent 50%);
            background-attachment: fixed;
            color: var(--text-main);
            min-height: 100vh;
            min-width: 320px;
            display: flex;
            flex-direction: column;
            transition: background-color 0.3s ease, color 0.3s ease;
        }

        [data-theme="light"] body {
            background-image: 
                radial-gradient(at 0% 0%, rgba(99, 102, 241, 0.08) 0px, transparent 50%),
                radial-gradient(at 100% 0%, rgba(6, 182, 212, 0.06) 0px, transparent 50%);
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

        [data-theme="light"] header {
            background: rgba(255, 255, 255, 0.88);
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

        [data-theme="light"] .brand-text h1 {
            background: linear-gradient(to right, #0f172a, #475569);
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

        [data-theme="light"] .nav-links {
            background: rgba(226, 232, 240, 0.8);
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
            gap: 12px;
        }

        .btn-theme {
            background: rgba(255, 255, 255, 0.05);
            border: 1px solid var(--border-color);
            color: var(--text-main);
            padding: 8px 14px;
            border-radius: 20px;
            font-size: 13px;
            font-weight: 600;
            cursor: pointer;
            display: flex;
            align-items: center;
            gap: 6px;
            transition: all 0.2s;
        }

        .btn-theme:hover {
            background: rgba(99, 102, 241, 0.15);
            border-color: var(--primary);
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
            font-weight: 500;
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
            gap: 16px;
            overflow-y: auto;
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
            gap: 6px;
        }

        .form-label {
            font-size: 13px;
            color: var(--text-muted);
            font-weight: 500;
        }

        .form-control {
            background: var(--bg-input);
            border: 1px solid var(--border-color);
            color: var(--text-main);
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
            padding: 9px;
            border-radius: var(--radius-sm);
            text-align: center;
            font-size: 13px;
            cursor: pointer;
            transition: all 0.2s;
            user-select: none;
            color: var(--text-main);
        }

        .hobby-card:hover {
            border-color: var(--primary-light);
            background: rgba(99, 102, 241, 0.1);
        }

        .hobby-card.selected {
            background: rgba(99, 102, 241, 0.2);
            border-color: var(--primary);
            color: var(--primary-light);
            font-weight: 600;
            box-shadow: 0 0 12px var(--primary-glow);
        }

        .chip-list {
            display: flex;
            flex-direction: column;
            gap: 6px;
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

        [data-theme="light"] .chip-item {
            background: rgba(0, 0, 0, 0.03);
        }

        .chip-item:hover {
            background: rgba(99, 102, 241, 0.1);
            border-color: var(--primary);
            color: var(--text-main);
            transform: translateX(3px);
        }

        .btn-clear-chat {
            background: transparent;
            border: 1px dashed var(--border-color);
            color: var(--text-muted);
            padding: 8px;
            border-radius: var(--radius-sm);
            font-size: 12px;
            cursor: pointer;
            width: 100%;
            transition: all 0.2s;
            margin-top: 4px;
        }

        .btn-clear-chat:hover {
            border-color: var(--danger);
            color: #fca5a5;
            background: rgba(239, 68, 68, 0.08);
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
            max-width: 84%;
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

        [data-theme="light"] .message-bot .message-content {
            background: #ffffff;
            box-shadow: 0 4px 20px rgba(0, 0, 0, 0.06);
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

        .badge-llm {
            background: rgba(168, 85, 247, 0.2);
            color: #d8b4fe;
            border: 1px solid rgba(168, 85, 247, 0.4);
            font-weight: 700;
        }

        .badge-fallback {
            background: rgba(59, 130, 246, 0.2);
            color: #93c5fd;
            border: 1px solid rgba(59, 130, 246, 0.4);
            font-weight: 700;
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

        .badge-pulsing {
            animation: pulseRAG 1.4s infinite;
        }

        @keyframes pulseRAG {
            0%, 100% { opacity: 1; transform: scale(1); }
            50% { opacity: 0.6; transform: scale(0.98); }
        }

        /* Typing Dots Animation */
        .typing-indicator {
            display: inline-flex;
            align-items: center;
            gap: 4px;
            padding: 4px 8px;
        }

        .typing-indicator span {
            width: 7px;
            height: 7px;
            border-radius: 50%;
            background: var(--primary-light);
            display: inline-block;
            animation: bounceDots 1.4s infinite ease-in-out both;
        }

        .typing-indicator span:nth-child(1) { animation-delay: -0.32s; }
        .typing-indicator span:nth-child(2) { animation-delay: -0.16s; }

        @keyframes bounceDots {
            0%, 80%, 100% { transform: scale(0.2); opacity: 0.3; }
            40% { transform: scale(1); opacity: 1; }
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

        [data-theme="light"] .rag-sources-accordion {
            background: rgba(241, 245, 249, 0.8);
        }

        .rag-sources-accordion summary {
            cursor: pointer;
            color: #6ee7b7;
            font-weight: 600;
            user-select: none;
            outline: none;
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

        [data-theme="light"] .rag-chunk-item {
            background: #ffffff;
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
            color: var(--text-muted);
            line-height: 1.5;
            margin: 0;
            white-space: pre-wrap;
        }

        .formula-box {
            background: rgba(0, 0, 0, 0.4);
            border: 1px solid rgba(255, 255, 255, 0.1);
            padding: 4px 10px;
            border-radius: 6px;
            font-family: 'JetBrains Mono', monospace;
            font-size: 14px;
            color: #38bdf8;
            margin: 4px 0;
            display: inline-block;
        }

        [data-theme="light"] .formula-box {
            background: #e2e8f0;
            border-color: rgba(0, 0, 0, 0.1);
            color: #0369a1;
        }

        /* Quiz Card */
        .quiz-card {
            background: rgba(30, 41, 59, 0.8);
            border: 1px solid var(--border-glow);
            border-radius: var(--radius-md);
            padding: 16px;
            margin-top: 16px;
        }

        [data-theme="light"] .quiz-card {
            background: #f8fafc;
            border-color: rgba(99, 102, 241, 0.3);
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
            color: var(--text-main);
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

        [data-theme="light"] .quiz-opt-btn {
            background: #ffffff;
        }

        .quiz-opt-btn:hover {
            border-color: var(--primary);
            background: rgba(99, 102, 241, 0.15);
        }

        .quiz-opt-btn.correct {
            background: rgba(16, 185, 129, 0.25) !important;
            border-color: #10b981 !important;
            color: #34d399 !important;
        }

        .quiz-opt-btn.wrong {
            background: rgba(239, 68, 68, 0.25) !important;
            border-color: #ef4444 !important;
            color: #f87171 !important;
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

        [data-theme="light"] .chat-input-bar {
            background: #f8fafc;
        }

        .chat-input {
            flex: 1;
            background: rgba(30, 41, 59, 0.6);
            border: 1px solid var(--border-color);
            color: var(--text-main);
            padding: 12px 18px;
            border-radius: 24px;
            font-size: 15px;
            outline: none;
            transition: all 0.2s;
        }

        [data-theme="light"] .chat-input {
            background: #ffffff;
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
            font-size: 16px;
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
            color: var(--text-main);
            margin-bottom: 6px;
        }

        .card-header p {
            font-size: 14px;
            color: var(--text-muted);
        }

        .dropzone {
            border: 2px dashed rgba(99, 102, 241, 0.4);
            border-radius: var(--radius-md);
            padding: 36px 20px;
            text-align: center;
            background: rgba(15, 23, 42, 0.4);
            cursor: pointer;
            transition: all 0.2s;
            margin-bottom: 16px;
        }

        [data-theme="light"] .dropzone {
            background: #ffffff;
        }

        .dropzone:hover, .dropzone.dragover {
            border-color: var(--secondary);
            background: rgba(6, 182, 212, 0.08);
        }

        .dropzone-icon {
            font-size: 38px;
            margin-bottom: 10px;
            color: var(--primary-light);
        }

        .dropzone-text {
            font-size: 15px;
            font-weight: 500;
            color: var(--text-main);
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

        /* Upload Progress Bar */
        .upload-progress-wrap {
            margin-top: 14px;
            background: rgba(15, 23, 42, 0.6);
            border: 1px solid var(--border-color);
            border-radius: var(--radius-sm);
            padding: 12px;
        }

        .progress-bar-outer {
            height: 8px;
            background: rgba(255, 255, 255, 0.1);
            border-radius: 4px;
            overflow: hidden;
            margin-top: 6px;
        }

        .progress-bar-inner {
            height: 100%;
            width: 0%;
            background: linear-gradient(90deg, var(--primary), var(--secondary));
            border-radius: 4px;
            transition: width 0.3s ease;
        }

        /* Books Table */
        .table-responsive {
            overflow-x: auto;
        }

        table {
            width: 100%;
            border-collapse: collapse;
            font-size: 13px;
        }

        th {
            text-align: left;
            padding: 10px 12px;
            color: var(--text-muted);
            border-bottom: 1px solid var(--border-color);
            font-weight: 600;
        }

        td {
            padding: 12px;
            border-bottom: 1px solid rgba(255, 255, 255, 0.05);
            color: var(--text-main);
        }

        [data-theme="light"] td {
            border-bottom: 1px solid rgba(0, 0, 0, 0.05);
        }

        .btn-tbl-action {
            padding: 5px 9px;
            font-size: 11px;
            border-radius: 6px;
            border: none;
            cursor: pointer;
            font-weight: 600;
            transition: all 0.2s;
            margin-right: 4px;
        }

        .btn-reindex {
            background: rgba(59, 130, 246, 0.2);
            color: #93c5fd;
            border: 1px solid rgba(59, 130, 246, 0.4);
        }

        .btn-reindex:hover {
            background: rgba(59, 130, 246, 0.4);
        }

        .btn-delete-book {
            background: rgba(239, 68, 68, 0.2);
            color: #fca5a5;
            border: 1px solid rgba(239, 68, 68, 0.4);
        }

        .btn-delete-book:hover {
            background: rgba(239, 68, 68, 0.4);
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

        [data-theme="light"] .steps-box {
            background: #ffffff;
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

        /* Mobile Responsiveness (min-width: 320px) */
        @media (max-width: 900px) {
            .chat-container {
                display: flex;
                flex-direction: column;
                height: auto;
                min-height: calc(100vh - 120px);
            }
            .chat-sidebar {
                order: 2;
                max-height: 400px;
            }
            .upload-layout {
                grid-template-columns: 1fr;
            }
            header {
                padding: 12px 16px;
            }
            .header-inner {
                flex-wrap: wrap;
            }
        }

        @media (max-width: 520px) {
            main {
                padding: 0 12px;
            }
            .message-bubble {
                max-width: 96%;
            }
            .nav-links {
                width: 100%;
                justify-content: space-around;
            }
            .nav-btn {
                padding: 6px 10px;
                font-size: 12px;
            }
            .header-actions {
                width: 100%;
                justify-content: space-between;
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
                <button id="themeToggle" class="btn-theme" onclick="toggleTheme()" title="Переключить тему оформления">
                    <span id="themeIcon">🌙</span> <span id="themeLabel">Тёмная</span>
                </button>
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
                            <option value="5">5 класс</option>
                            <option value="6">6 класс</option>
                            <option value="7" selected>7 класс</option>
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
                            <button class="chip-item" onclick="askPreset('Объясни квадратные уравнения')">📐 Квадратные уравнения</button>
                            <button class="chip-item" onclick="askPreset('Что такое Закон Ома?')">🔌 Закон Ома</button>
                            <button class="chip-item" onclick="askPreset('Объясни теорему Пифагора')">🔺 Теорема Пифагора</button>
                            <button class="chip-item" onclick="askPreset('Как устроен фотосинтез?')">🌿 Фотосинтез</button>
                            <button class="chip-item" onclick="askPreset('Как работает сила гравитации?')">🪐 Гравитация</button>
                            <button class="chip-item" onclick="askPreset('Объясни алгоритм сортировки')">💻 Алгоритм сортировки</button>
                        </div>
                    </div>

                    <button class="btn-clear-chat" onclick="clearChatHistory()">🗑️ Очистить историю диалога</button>
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
                        <p>Загрузите школьный учебник в формате PDF. Система автоматически извлечёт текст, разобьёт на чанки (1000/200 с защитой формул) и добавит в RAG-индекс.</p>
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
                        <div class="dropzone-sub">Поддерживаются стандартные PDF с текстовым слоем (до 100 МБ)</div>
                        <input type="file" id="fileInput" accept=".pdf" style="display:none;" onchange="handleFileSelected(this.files)">
                    </div>

                    <button id="btnUpload" class="btn-primary" onclick="uploadTextbook()" disabled>Загрузить и проиндексировать в RAG</button>

                    <!-- Animated Progress Bar -->
                    <div id="uploadProgressWrap" class="upload-progress-wrap" style="display:none;">
                        <div style="display:flex; justify-content:space-between; font-size:12px; color:var(--text-muted);">
                            <span id="uploadProgressText">Загрузка файла и чанкинг...</span>
                            <span id="uploadProgressPct" style="font-weight:700; color:#38bdf8;">0%</span>
                        </div>
                        <div class="progress-bar-outer">
                            <div id="uploadProgressBar" class="progress-bar-inner"></div>
                        </div>
                    </div>

                    <div id="uploadStatus" style="margin-top: 16px; display: none;"></div>
                </div>

                <div class="card">
                    <div class="card-header">
                        <h2>📖 Активные учебники в RAG</h2>
                        <p>Список проиндексированных пособий. Система проверяет факты и выдает цитаты с номерами страниц.</p>
                    </div>

                    <div class="table-responsive">
                        <table>
                            <thead>
                                <tr>
                                    <th>Предмет</th>
                                    <th>Файл / Источник</th>
                                    <th>Размер & Дата</th>
                                    <th>Чанков</th>
                                    <th>Действия</th>
                                </tr>
                            </thead>
                            <tbody id="textbooksTableBody">
                                <tr><td colspan="5" style="text-align:center; color:var(--text-muted);">Загрузка списка учебников...</td></tr>
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
                    <h3 style="font-size: 15px; margin-bottom: 14px; color: var(--text-main);">📱 5 простых шагов для теста в мессенджере:</h3>
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
        let waitNoticeTimer = null;

        // Theme Toggle
        function applyTheme(theme) {
            document.documentElement.setAttribute('data-theme', theme);
            const icon = document.getElementById('themeIcon');
            const label = document.getElementById('themeLabel');
            if (theme === 'light') {
                if (icon) icon.innerText = '☀️';
                if (label) label.innerText = 'Светлая';
            } else {
                if (icon) icon.innerText = '🌙';
                if (label) label.innerText = 'Тёмная';
            }
            localStorage.setItem('student_theme', theme);
        }

        function toggleTheme() {
            const current = document.documentElement.getAttribute('data-theme') || 'dark';
            const next = current === 'light' ? 'dark' : 'light';
            applyTheme(next);
        }

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

        function clearChatHistory() {
            const container = document.getElementById('chatMessages');
            container.innerHTML = `
                <div class="message-bubble message-bot">
                    <div class="message-header">🤖 Абстрактный Репетитор</div>
                    <div class="message-content">
                        История диалога очищена. Задай мне новый школьный вопрос или выбери тему слева!
                    </div>
                </div>
            `;
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

            // 2. Append Loading Placeholder with 3-dot animation
            const loadingMsg = document.createElement('div');
            loadingMsg.className = 'message-bubble message-bot';
            loadingMsg.id = 'loadingBubble';
            loadingMsg.innerHTML = `
                <div class="message-header">🤖 Репетитор подбирает аналогию...</div>
                <div class="message-content" id="loadingContent">
                    <div class="badges-bar">
                        <span class="badge badge-rag-active badge-pulsing">🔵 ⚡ RAG поиск по учебникам...</span>
                    </div>
                    <div style="display:flex; align-items:center; gap:8px; color:var(--text-muted); font-size:14px;">
                        <span>Генерация метафоры через «${escapeHtml(currentHobby)}»</span>
                        <div class="typing-indicator"><span></span><span></span><span></span></div>
                    </div>
                </div>
            `;
            messagesContainer.appendChild(loadingMsg);
            messagesContainer.scrollTop = messagesContainer.scrollHeight;

            // 3. 15-second timeout notification
            if (waitNoticeTimer) clearTimeout(waitNoticeTimer);
            waitNoticeTimer = setTimeout(() => {
                const loadingContent = document.getElementById('loadingContent');
                if (loadingContent) {
                    const notice = document.createElement('div');
                    notice.id = 'timeoutNotice';
                    notice.style.marginTop = '10px';
                    notice.style.fontSize = '12px';
                    notice.style.color = '#fbbf24';
                    notice.innerHTML = '⚡ Запрос обрабатывается дольше обычного, подбираем лучшую метафору и формулу...';
                    loadingContent.appendChild(notice);
                }
            }, 15000);

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

                if (waitNoticeTimer) clearTimeout(waitNoticeTimer);
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
                if (waitNoticeTimer) clearTimeout(waitNoticeTimer);
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

            const latency = data.latency_ms || 180;
            const latencySec = (latency / 1000).toFixed(1);
            const ragHits = data.rag_hits || (data.rag_chunks ? data.rag_chunks.length : 0);

            // Источник: LLM vs Fallback
            let sourceBadgeHtml = '';
            if (data.source && (data.source.includes('giga') || data.source === 'llm')) {
                sourceBadgeHtml = '<span class="badge badge-llm">🧠 LLM (GigaChat)</span>';
            } else {
                sourceBadgeHtml = '<span class="badge badge-fallback">⚡ Каталог метафор (Fallback)</span>';
            }

            // Бейдж RAG: зеленый если найден контекст, серый если не найден
            let ragBadgeHtml = '';
            if (ragHits > 0) {
                ragBadgeHtml = `<span class="badge badge-rag-active" title="Извлечено ${ragHits} фрагментов из учебника">🟢 📚 RAG: ${ragHits} чанка</span>`;
            } else {
                ragBadgeHtml = `<span class="badge badge-rag-idle" title="Контекст не найден в учебниках">⚪ 📚 RAG: не использован</span>`;
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
                        ${sourceBadgeHtml}
                        ${ragBadgeHtml}
                        <span class="badge badge-speed">⚡ ${latencySec} сек (${latency} мс)</span>
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

        // Upload Logic with Progress Bar
        function handleFileSelected(files) {
            if (!files || files.length === 0) return;
            selectedFile = files[0];
            const sizeKb = (selectedFile.size / 1024).toFixed(1);
            document.getElementById('dropzoneText').innerHTML = `✅ <strong>Выбран файл:</strong> ${escapeHtml(selectedFile.name)} (${sizeKb} КБ)`;
            const btn = document.getElementById('btnUpload');
            btn.disabled = false;
            btn.innerHTML = `🚀 Загрузить «${escapeHtml(selectedFile.name)}»`;
        }

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
            const progressWrap = document.getElementById('uploadProgressWrap');
            const progressBar = document.getElementById('uploadProgressBar');
            const progressPct = document.getElementById('uploadProgressPct');
            const progressText = document.getElementById('uploadProgressText');
            const subject = document.getElementById('uploadSubject').value;

            btn.disabled = true;
            btn.innerText = '⏳ Индексация учебника...';
            statusBox.style.display = 'none';
            progressWrap.style.display = 'block';

            // Simulate progress animation
            let progress = 10;
            progressBar.style.width = '10%';
            progressPct.innerText = '10%';
            progressText.innerText = 'Чтение PDF и проверка текстового слоя...';

            const progressInterval = setInterval(() => {
                if (progress < 85) {
                    progress += 15;
                    progressBar.style.width = progress + '%';
                    progressPct.innerText = progress + '%';
                    if (progress > 40) progressText.innerText = 'Генерация чанков (1000/200) и фильтрация формул...';
                    if (progress > 70) progressText.innerText = 'Построение BM25 индекса и расчет весов...';
                }
            }, 300);

            const formData = new FormData();
            formData.append('file', selectedFile);
            formData.append('subject', subject);

            try {
                const resp = await fetch('/api/student/upload_textbook', {
                    method: 'POST',
                    body: formData
                });

                clearInterval(progressInterval);
                progressBar.style.width = '100%';
                progressPct.innerText = '100%';
                progressText.innerText = 'Готово!';

                const res = await resp.json();
                statusBox.style.display = 'block';

                if (res.status === 'ok') {
                    let warnHtml = '';
                    if (res.warning) {
                        warnHtml = `<div style="margin-top:8px; color:#fbbf24; font-size:13px;">⚠️ ${escapeHtml(res.warning)}</div>`;
                    }
                    statusBox.innerHTML = `
                        <div style="background:rgba(16,185,129,0.15); border:1px solid #10b981; padding:12px; border-radius:8px; color:#6ee7b7;">
                            ✅ ${escapeHtml(res.message)}<br>
                            <strong>Извлечено чанков:</strong> ${res.chunks_count} | <strong>Предмет:</strong> ${escapeHtml(res.subject)}
                            ${warnHtml}
                        </div>
                    `;
                    loadTextbooksList();
                } else {
                    statusBox.innerHTML = `
                        <div style="background:rgba(239,68,68,0.15); border:1px solid #ef4444; padding:12px; border-radius:8px; color:#fca5a5;">
                            ❌ ${escapeHtml(res.message)}
                        </div>
                    `;
                }
            } catch (err) {
                clearInterval(progressInterval);
                console.error(err);
                statusBox.style.display = 'block';
                statusBox.innerHTML = `
                    <div style="background:rgba(239,68,68,0.15); border:1px solid #ef4444; padding:12px; border-radius:8px; color:#fca5a5;">
                        ❌ Ошибка загрузки файла на сервер.
                    </div>
                `;
            } finally {
                btn.disabled = false;
                btn.innerText = 'Загрузить и проиндексировать в RAG';
                setTimeout(() => { progressWrap.style.display = 'none'; }, 2000);
            }
        }

        async function reindexTextbook(subject) {
            try {
                const resp = await fetch('/api/student/textbook/reindex', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ subject: subject })
                });
                const res = await resp.json();
                if (res.status === 'ok') {
                    alert(`✅ ${res.message}`);
                    loadTextbooksList();
                } else {
                    alert(`❌ ${res.message}`);
                }
            } catch (e) {
                alert('Ошибка переиндексации: ' + e);
            }
        }

        async function deleteTextbook(subject) {
            if (!confirm(`Вы уверены, что хотите удалить индекс по предмету «${subject}»?`)) return;
            try {
                const resp = await fetch('/api/student/textbook/delete', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ subject: subject })
                });
                const res = await resp.json();
                if (res.status === 'ok') {
                    loadTextbooksList();
                } else {
                    alert(`❌ ${res.message}`);
                }
            } catch (e) {
                alert('Ошибка удаления: ' + e);
            }
        }

        async function loadTextbooksList() {
            const tbody = document.getElementById('textbooksTableBody');
            try {
                const resp = await fetch('/api/student/textbooks');
                const data = await resp.json();

                if (!data.textbooks || data.textbooks.length === 0) {
                    tbody.innerHTML = '<tr><td colspan="5" style="text-align:center; color:var(--text-muted);">В базе пока нет проиндексированных учебников. Загрузите первый!</td></tr>';
                    return;
                }

                tbody.innerHTML = data.textbooks.map(tb => `
                    <tr>
                        <td><strong>${escapeHtml(tb.subject.toUpperCase())}</strong></td>
                        <td>${tb.sources ? tb.sources.map(s => escapeHtml(s)).join(', ') : 'Учебник'}</td>
                        <td><span style="color:var(--text-muted); font-size:12px;">${tb.size_kb ? tb.size_kb + ' КБ · ' : ''}${tb.date || '—'}</span></td>
                        <td><span style="font-family:'JetBrains Mono',monospace; color:#38bdf8; font-weight:700;">${tb.chunks_count} чанков</span></td>
                        <td>
                            <button class="btn-tbl-action btn-reindex" onclick="reindexTextbook('${tb.subject}')" title="Переиндексировать этот предмет">🔄</button>
                            <button class="btn-tbl-action btn-delete-book" onclick="deleteTextbook('${tb.subject}')" title="Удалить индекс">🗑️</button>
                        </td>
                    </tr>
                `).join('');
            } catch (e) {
                console.error(e);
                tbody.innerHTML = '<tr><td colspan="5" style="text-align:center; color:var(--danger);">Не удалось загрузить список учебников.</td></tr>';
            }
        }

        // Init
        document.addEventListener('DOMContentLoaded', () => {
            const savedTheme = localStorage.getItem('student_theme') || 'dark';
            applyTheme(savedTheme);
            loadTextbooksList();
        });
    </script>
</body>
</html>
"""
