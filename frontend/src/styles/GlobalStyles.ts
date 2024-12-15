import { createGlobalStyle } from 'styled-components';

export const GlobalStyles = createGlobalStyle`
    :root {
        --bg-color: ${() => window.Telegram.WebApp.themeParams.bg_color};
        --text-color: ${() => window.Telegram.WebApp.themeParams.text_color};
        --hint-color: ${() => window.Telegram.WebApp.themeParams.hint_color};
        --link-color: ${() => window.Telegram.WebApp.themeParams.link_color};
        --button-color: ${() => window.Telegram.WebApp.themeParams.button_color};
        --button-text-color: ${() => window.Telegram.WebApp.themeParams.button_text_color};
        --secondary-bg-color: ${() => window.Telegram.WebApp.themeParams.secondary_bg_color};
    }

    body {
        margin: 0;
        padding: 0;
        font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', 'Roboto', 'Oxygen',
            'Ubuntu', 'Cantarell', 'Fira Sans', 'Droid Sans', 'Helvetica Neue',
            sans-serif;
        -webkit-font-smoothing: antialiased;
        -moz-osx-font-smoothing: grayscale;
        background-color: var(--bg-color);
        color: var(--text-color);
    }

    * {
        box-sizing: border-box;
    }

    a {
        color: var(--link-color);
        text-decoration: none;
        
        &:hover {
            text-decoration: underline;
        }
    }

    button {
        background-color: var(--button-color);
        color: var(--button-text-color);
        border: none;
        padding: 8px 16px;
        border-radius: 8px;
        cursor: pointer;
        font-size: 14px;
        
        &:disabled {
            opacity: 0.6;
            cursor: not-allowed;
        }
    }

    .card {
        background-color: var(--secondary-bg-color);
        border-radius: 12px;
        padding: 16px;
        margin: 8px 0;
    }

    .hint-text {
        color: var(--hint-color);
        font-size: 14px;
    }
`; 