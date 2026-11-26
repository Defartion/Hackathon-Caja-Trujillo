import { Link, Route, Routes } from "react-router-dom";
import Bandeja from "./pages/Bandeja";
import Comite from "./pages/Comite";
import Ficha from "./pages/Ficha";
import NuevaSolicitud from "./pages/NuevaSolicitud";

export default function App() {
  return (
    <>
      <header className="barra">
        <Link to="/" style={{ textDecoration: "none", color: "inherit" }}>
          <div className="marca">
            Cuota<span>Flex</span>
          </div>
        </Link>
        <div className="sub">Herramienta del asesor de negocios · datos sintéticos</div>
        <Link to="/nueva" className="btn btn-primario" style={{ marginLeft: "auto", textDecoration: "none" }}>
          Nueva solicitud
        </Link>
      </header>
      <main className="contenido">
        <Routes>
          <Route path="/" element={<Bandeja />} />
          <Route path="/cliente/:id" element={<Ficha />} />
          <Route path="/nueva" element={<NuevaSolicitud />} />
          <Route path="/comite/:id" element={<Comite />} />
        </Routes>
      </main>
    </>
  );
}
