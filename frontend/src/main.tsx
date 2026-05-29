import { ClerkProvider } from '@clerk/react';
import { StrictMode } from 'react';
import { createRoot } from 'react-dom/client';
import './index.css';
import App from './App.tsx';

const clerkKey = import.meta.env.VITE_CLERK_PUBLISHABLE_KEY;

const clerkAppearance = {
  variables: {
    colorPrimary: '#d97757',
    colorTextOnPrimaryBackground: '#1c1916',
    colorBackground: '#1c1916',
    colorInputBackground: '#262220',
    colorInputText: '#f0ddd0',
    colorText: '#f0ddd0',
    colorTextSecondary: '#8a7a6f',
    colorNeutral: '#f0ddd0',
    colorDanger: '#cc5f5f',
    colorSuccess: '#7dcc8a',
    colorWarning: '#ccaa44',
    borderRadius: '0px',
    fontFamily: "'Space Mono', monospace",
    fontSize: '13px',
    fontSmoothing: 'antialiased',
  },
  elements: {
    card: {
      backgroundColor: '#1c1916',
      border: '1px solid #312d29',
      borderRadius: '0',
      boxShadow: '0 0 40px rgba(217,119,87,0.1)',
    },
    headerTitle: {
      fontFamily: "'Silkscreen', cursive",
      color: '#d97757',
      letterSpacing: '0.14em',
      textTransform: 'uppercase' as const,
    },
    headerSubtitle: {
      color: '#8a7a6f',
      fontFamily: "'Space Mono', monospace",
    },
    formButtonPrimary: {
      backgroundColor: '#d97757',
      color: '#1c1916',
      borderRadius: '0',
      fontWeight: '700',
      letterSpacing: '0.1em',
      textTransform: 'uppercase' as const,
      fontSize: '11px',
      boxShadow: '0 0 12px rgba(217,119,87,0.2)',
      '&:hover': {
        backgroundColor: '#a8431f',
      },
    },
    formFieldInput: {
      backgroundColor: '#262220',
      border: '1px solid #312d29',
      borderRadius: '0',
      color: '#f0ddd0',
      fontFamily: "'Space Mono', monospace",
      '&:focus': {
        borderColor: 'rgba(217,119,87,0.4)',
        boxShadow: 'none',
      },
    },
    formFieldLabel: {
      color: '#8a7a6f',
      fontFamily: "'Space Mono', monospace",
      fontSize: '10px',
      letterSpacing: '0.12em',
      textTransform: 'uppercase' as const,
    },
    footerActionLink: {
      color: '#d97757',
      '&:hover': {
        color: '#e89b7d',
      },
    },
    socialButtonsBlockButton: {
      backgroundColor: '#262220',
      border: '1px solid #312d29',
      borderRadius: '0',
      color: '#f0ddd0',
      '&:hover': {
        backgroundColor: '#312d29',
      },
    },
    dividerLine: {
      backgroundColor: '#312d29',
    },
    dividerText: {
      color: '#5e524a',
    },
    identityPreview: {
      backgroundColor: '#262220',
      border: '1px solid #312d29',
      borderRadius: '0',
    },
    userButtonPopoverCard: {
      backgroundColor: '#1c1916',
      border: '1px solid #312d29',
      borderRadius: '0',
    },
    userButtonPopoverActionButton: {
      color: '#f0ddd0',
      '&:hover': {
        backgroundColor: '#262220',
      },
    },
    userButtonAvatarBox: {
      borderRadius: '0',
    },
    avatarBox: {
      borderRadius: '0',
    },
    badge: {
      borderRadius: '0',
    },
    modalBackdrop: {
      backgroundColor: 'rgba(20,18,16,0.85)',
    },
  },
};

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <ClerkProvider
      publishableKey={clerkKey}
      afterSignOutUrl="/"
      appearance={clerkAppearance}
    >
      <App />
    </ClerkProvider>
  </StrictMode>,
);
