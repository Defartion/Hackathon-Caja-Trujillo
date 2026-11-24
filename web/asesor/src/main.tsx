import React from "react";
import ReactDOM from "react-dom/client";
import { BrowserRouter } from "react-router-dom";
import App from "./App"
import { ConSesion } from "./sesion";
import "./styles.css";

ReactDOM.createRoot(document.getElementById("root")!).render(
  <React.StrictMode>
    <BrowserRouter>
      <ConSesion rol="asesor" titulo="Herramienta del asesor de negocios">
        <App />
      </ConSesion>
    </BrowserRouter>
  </React.StrictMode>,
);
