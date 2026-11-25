import { Route, Routes } from "react-router-dom";
import Lateral, { OPCIONES_ASESOR } from "./Lateral";
import Bandeja from "./pages/Bandeja";
import Ficha from "./pages/Ficha";
import Prestamos from "./pages/Prestamos";

export default function App() {
  return (
    <Lateral rol="Asesor de negocios" opciones={OPCIONES_ASESOR}>
      <Routes>
        <Route path="/" element={<Bandeja />} />
        <Route path="/cliente/:id" element={<Ficha />} />
        <Route path="/prestamos" element={<Prestamos />} />
      </Routes>
    </Lateral>
  );
}
