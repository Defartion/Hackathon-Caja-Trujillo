import '@fontsource-variable/archivo/wdth.css';
import './tema.css';
import { StrictMode } from 'react';
import { createRoot } from 'react-dom/client';
import App from './App'
import { ConSesion } from './sesion';
import './styles.css';

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <ConSesion rol="supervisor" titulo="Tablero de simulación de cartera">
      <App />
    </ConSesion>
  </StrictMode>,
);
