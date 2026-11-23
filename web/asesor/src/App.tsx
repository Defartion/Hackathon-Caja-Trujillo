import { Link, Route, Routes } from "react-router-dom";
import Bandeja from "./pages/Bandeja";
import Ficha from "./pages/Ficha";

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
      </header>
      <main className="contenido">
        <Routes>
          <Route path="/" element={<Bandeja />} />
          <Route path="/cliente/:id" element={<Ficha />} />
        </Routes>
      </main>
    </>
  );
}
