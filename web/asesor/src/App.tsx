import { Route, Routes } from "react-router-dom";
import Lateral, { OPCIONES_ASESOR } from "./Lateral";
import Bandeja from "./pages/Bandeja";
import Comite from "./pages/Comite";
import ComiteLista from "./pages/ComiteLista";
import Ficha from "./pages/Ficha";
import NuevaSolicitud from "./pages/NuevaSolicitud";
import PrestamoDetalle from "./pages/PrestamoDetalle";
import Prestamos from "./pages/Prestamos";

export default function App() {
  return (
    <Lateral rol="Asesor de negocios" opciones={OPCIONES_ASESOR}>
      <Routes>
        <Route path="/" element={<Bandeja />} />
        <Route path="/cliente/:id" element={<Ficha />} />
        <Route path="/nueva" element={<NuevaSolicitud />} />
        <Route path="/comite" element={<ComiteLista />} />
        <Route path="/comite/:id" element={<Comite />} />
        <Route path="/prestamos" element={<Prestamos />} />
        <Route path="/prestamos/:id" element={<PrestamoDetalle />} />
      </Routes>
    </Lateral>
  );
}
