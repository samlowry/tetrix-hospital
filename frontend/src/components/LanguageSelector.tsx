import React from 'react';
import styled from 'styled-components';
import { useLanguage } from '../i18n/LanguageContext';

const ButtonContainer = styled.div`
  display: flex;
  gap: 10px;
  justify-content: center;
  margin-bottom: 20px;
`;

const LangButton = styled.button<{ isActive: boolean }>`
  padding: 8px 16px;
  border-radius: 8px;
  border: none;
  background: ${props => props.isActive ? 'var(--tg-theme-button-color)' : 'var(--tg-theme-secondary-bg-color)'};
  color: ${props => props.isActive ? 'var(--tg-theme-button-text-color)' : 'var(--tg-theme-text-color)'};
  cursor: pointer;
  transition: all 0.2s ease;

  &:hover {
    opacity: 0.8;
  }
`;

export const LanguageSelector: React.FC = () => {
  const { language, setLanguage, t } = useLanguage();

  const handleLanguageChange = (lang: 'en' | 'ru') => {
    setLanguage(lang);
    window.location.hash = `lang=${lang}`;
  };

  return (
    <ButtonContainer>
      <LangButton
        isActive={language === 'ru'}
        onClick={() => handleLanguageChange('ru')}
      >
        {t('buttons.lang_ru')}
      </LangButton>
      <LangButton
        isActive={language === 'en'}
        onClick={() => handleLanguageChange('en')}
      >
        {t('buttons.lang_en')}
      </LangButton>
    </ButtonContainer>
  );
}; 