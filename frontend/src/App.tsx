import { useState, useCallback, useEffect } from 'react';
import { useAuth, useSession, SignIn } from '@clerk/react';
import { BrowserRouter, Routes, Route } from 'react-router-dom';
import Shell from './components/Shell';
import PixelTransition from './components/PixelTransition';
import Landing from './pages/Landing';
import DocsPage from './pages/DocsPage';
import Dashboard from './pages/Dashboard';
import Agents from './pages/Agents';
import Verify from './pages/Verify';
import Compare from './pages/Compare';
import Attestation from './pages/Attestation';
import { setTokenGetter } from './lib/api';

export default function App() {
  const { isSignedIn, isLoaded } = useAuth();
  const { session } = useSession();
  const [showSignIn, setShowSignIn] = useState(false);
  const [transitioning, setTransitioning] = useState(false);
  const [justSignedIn, setJustSignedIn] = useState(false);

  useEffect(() => {
    if (session) {
      setTokenGetter(() => session.getToken());
    } else {
      setTokenGetter(() => Promise.resolve(null));
    }
  }, [session]);

  const handleEnter = useCallback(() => {
    setShowSignIn(true);
  }, []);

  const handleTransitionComplete = useCallback(() => {
    setTransitioning(false);
  }, []);

  if (isLoaded && isSignedIn && !justSignedIn && showSignIn) {
    setJustSignedIn(true);
    setShowSignIn(false);
    setTransitioning(true);
  }

  if (!isLoaded) return null;

  if (!isSignedIn) {
    return (
      <BrowserRouter>
        <Routes>
          <Route path="/docs" element={<DocsPage />} />
          <Route path="*" element={
            <>
              <Landing onEnter={handleEnter} />
              {showSignIn && (
                <div className="fixed inset-0 z-[100] flex items-center justify-center"
                  style={{ backgroundColor: 'rgba(20,18,16,0.85)' }}>
                  <div className="fixed inset-0 pointer-events-none z-[101]"
                    style={{
                      background: 'repeating-linear-gradient(0deg, rgba(0,0,0,0.06) 0 1px, transparent 1px 3px)',
                      mixBlendMode: 'multiply',
                    }}
                  />
                  <div className="relative z-[102]">
                    <button
                      onClick={() => setShowSignIn(false)}
                      className="absolute -top-10 right-0 text-[11px] text-muted hover:text-peach tracking-[0.1em] transition-colors"
                    >
                      ESC TO CLOSE
                    </button>
                    <SignIn routing="hash" />
                  </div>
                </div>
              )}
            </>
          } />
        </Routes>
      </BrowserRouter>
    );
  }

  return (
    <BrowserRouter>
      <PixelTransition active={transitioning} onComplete={handleTransitionComplete}>
        <Routes>
          <Route path="/docs" element={<DocsPage />} />
          <Route element={<Shell />}>
            <Route index element={<Dashboard />} />
            <Route path="agents" element={<Agents />} />
            <Route path="verify" element={<Verify />} />
            <Route path="compare" element={<Compare />} />
            <Route path="attestation" element={<Attestation />} />
          </Route>
        </Routes>
      </PixelTransition>
    </BrowserRouter>
  );
}
