import { createGlobalStyle } from 'styled-components';

export const GlobalStyles = createGlobalStyle`
    body {
        margin: 0;
        padding: 0;
        font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', 'Roboto', 'Oxygen',
            'Ubuntu', 'Cantarell', 'Fira Sans', 'Droid Sans', 'Helvetica Neue',
            sans-serif;
        -webkit-font-smoothing: antialiased;
        -moz-osx-font-smoothing: grayscale;
        background-color: var(--tg-theme-bg-color);
        color: var(--tg-theme-text-color);
    }

    * {
        box-sizing: border-box;
    }

    a {
        color: var(--tg-theme-link-color);
        text-decoration: none;
        
        &:hover {
            text-decoration: underline;
        }
    }

    button {
        background-color: var(--tg-theme-button-color);
        color: var(--tg-theme-button-text-color);
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
        background-color: var(--tg-theme-secondary-bg-color);
        border-radius: 12px;
        padding: 16px;
        margin: 8px 0;
    }

    .hint-text {
        color: var(--tg-theme-hint-color);
        font-size: 14px;
    }
`; 