// Casos estrella de la demo (datos sintéticos). La captura es la misma que usa el lote B en
// data/ciclos/casos_estrella.json; el crédito sigue docs/demo/CASOS_ESTRELLA.md.
import type { EstadoMes, FormCredito, FormNegocio } from "./formularios";
import { creditoPorDefecto } from "./formularios";

export interface CasoEstrella {
  id: string;
  nombre: string;
  resumen: string;
  negocio: FormNegocio;
  credito: FormCredito;
}

function mesesEstado(altos: number[], bajos: number[]): EstadoMes[] {
  return Array.from({ length: 12 }, (_, i) => (altos.includes(i + 1) ? "alto" : bajos.includes(i + 1) ? "bajo" : "normal"));
}

export const CASOS_ESTRELLA: CasoEstrella[] = [
  {
    id: "E001",
    nombre: "Rosa",
    resumen: "Arroz en Chepén · cosecha en junio y julio",
    negocio: {
      cliente_id: "E001",
      nombre: "Rosa",
      sector: "agricultura",
      actividad: "arroz",
      zona: { departamento: "La Libertad", provincia: "Chepén", distrito: null },
      fecha_inicio: "2026-12-01",
      meses: "24",
      ventas_mes_alto: "16800",
      ventas_mes_normal: "7000",
      ventas_mes_bajo: "1750",
      meses_estado: mesesEstado([6, 7], [1, 2, 3]),
      costo_ventas_pct: "58",
      gastos_operativos: "600",
      gastos_tributarios: "80",
      carga_familiar: "1100",
      otras_deudas_cuota: "0",
      evidencias: [{ tipo: "yape", meses: "6", monto: "4100" }],
    },
    credito: { ...creditoPorDefecto("24"), monto: "7000" },
  },
  {
    id: "E002",
    nombre: "Martín",
    resumen: "Pesca artesanal en Pacasmayo · veda de mayo a setiembre",
    negocio: {
      cliente_id: "E002",
      nombre: "Martín",
      sector: "pesca",
      actividad: "pesca artesanal",
      zona: { departamento: "La Libertad", provincia: "Pacasmayo", distrito: null },
      // Desembolso al inicio de la veda: así la gracia no pasa de 4 meses (con el 30/04 serían 5).
      fecha_inicio: "2027-06-30",
      meses: "12",
      ventas_mes_alto: "13500",
      ventas_mes_normal: "9500",
      ventas_mes_bajo: "2800",
      meses_estado: mesesEstado([1, 2, 3], [5, 6, 7, 8, 9]),
      costo_ventas_pct: "58",
      gastos_operativos: "390",
      gastos_tributarios: "90",
      carga_familiar: "900",
      otras_deudas_cuota: "0",
      evidencias: [{ tipo: "boletas", meses: "3", monto: "4100" }],
    },
    credito: { ...creditoPorDefecto("12"), monto: "5200" },
  },
  {
    id: "E003",
    nombre: "Luis",
    resumen: "Bodega en Trujillo · ya paga S/ 380 de otras deudas",
    negocio: {
      cliente_id: "E003",
      nombre: "Luis",
      sector: "comercio",
      actividad: "bodega",
      zona: { departamento: "La Libertad", provincia: "Trujillo", distrito: null },
      fecha_inicio: "2026-12-01",
      meses: "12",
      ventas_mes_alto: "7200",
      ventas_mes_normal: "6000",
      ventas_mes_bajo: "5100",
      meses_estado: mesesEstado([7, 12], [2, 3]),
      costo_ventas_pct: "70",
      gastos_operativos: "330",
      gastos_tributarios: "70",
      carga_familiar: "800",
      otras_deudas_cuota: "380",
      evidencias: [{ tipo: "yape", meses: "3", monto: "3100" }],
    },
    credito: { ...creditoPorDefecto("12"), monto: "8000" },
  },
];

export const casoPorId = (id: string | undefined) => CASOS_ESTRELLA.find((c) => c.id === id);

/** Copia profunda para no mutar el caso al editar el formulario. */
export const copiar = <T,>(v: T): T => JSON.parse(JSON.stringify(v)) as T;
