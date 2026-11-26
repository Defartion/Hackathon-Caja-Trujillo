import { Cell, Label, Pie, PieChart, ResponsiveContainer, Tooltip } from 'recharts';
import type { Resumen } from '../api';
import { COLOR_PRODUCTO, NOMBRE_PRODUCTO } from '../colores';
import { entero } from '../formato';
import TarjetaGrafico from './TarjetaGrafico';

const ORDEN = ['fija', 'aplazamiento', 'estacional'] as const;

interface Seg {
  id: string;
  nombre: string;
  valor: number;
  pct: number;
}

export default function GraficoProductos({ mix }: { mix: Resumen['mix_productos'] }) {
  const total = ORDEN.reduce((s, k) => s + (mix[k] ?? 0), 0);
  const datos: Seg[] = ORDEN.filter((k) => (mix[k] ?? 0) > 0).map((k) => ({
    id: k,
    nombre: NOMBRE_PRODUCTO[k],
    valor: mix[k] ?? 0,
    pct: total ? Math.round(((mix[k] ?? 0) / total) * 100) : 0,
  }));

  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const etiqueta = (p: any) => {
    const RAD = Math.PI / 180;
    const r = p.outerRadius + 14;
    const x = p.cx + r * Math.cos(-p.midAngle * RAD);
    const y = p.cy + r * Math.sin(-p.midAngle * RAD);
    return (
      <text x={x} y={y} textAnchor={x > p.cx ? 'start' : 'end'} dominantBaseline="central" fontSize={12} fill="#172033">
        {p.nombre} {p.pct}%
      </text>
    );
  };

  const grafico = (
    <div style={{ display: 'flex', flexDirection: 'column', height: '100%' }}>
      <div style={{ flex: 1, minHeight: 0 }}>
        <ResponsiveContainer width="100%" height="100%">
          <PieChart margin={{ top: 10, right: 60, bottom: 10, left: 60 }}>
            <Tooltip
              formatter={(v: number, _n: string, item: { payload?: Seg }) => [
                `${entero(v)} créditos (${item.payload?.pct ?? 0}%)`,
                item.payload?.nombre ?? '',
              ]}
            />
            <Pie
              data={datos}
              dataKey="valor"
              nameKey="nombre"
              innerRadius="55%"
              outerRadius="78%"
              stroke="#fff"
              strokeWidth={2}
              paddingAngle={0}
              startAngle={90}
              endAngle={-270}
              isAnimationActive={false}
              label={etiqueta}
              labelLine={false}
            >
              {datos.map((d) => (
                <Cell key={d.id} fill={COLOR_PRODUCTO[d.id]} />
              ))}
              <Label
                position="center"
                // eslint-disable-next-line @typescript-eslint/no-explicit-any
                content={(props: any) => {
                  const { cx, cy } = props.viewBox ?? {};
                  if (typeof cx !== 'number') return null;
                  return (
                    <g>
                      <text x={cx} y={cy - 4} textAnchor="middle" fontSize={22} fontWeight={700} fill="#172033">
                        {entero(total)}
                      </text>
                      <text x={cx} y={cy + 14} textAnchor="middle" fontSize={12} fill="#5A6478">
                        créditos
                      </text>
                    </g>
                  );
                }}
              />
            </Pie>
          </PieChart>
        </ResponsiveContainer>
      </div>
      <div className="leyenda" style={{ justifyContent: 'center' }}>
        {datos.map((d) => (
          <span key={d.id} className="leyenda-item estatico">
            <span className="muestra" style={{ background: COLOR_PRODUCTO[d.id] }} aria-hidden="true" />
            {d.nombre}
          </span>
        ))}
      </div>
    </div>
  );

  const tabla = (
    <table className="tabla">
      <thead>
        <tr>
          <th>Producto</th>
          <th className="num">Créditos</th>
          <th className="num">Participación</th>
        </tr>
      </thead>
      <tbody>
        {datos.map((d) => (
          <tr key={d.id}>
            <td>{d.nombre}</td>
            <td className="num">{entero(d.valor)}</td>
            <td className="num">{d.pct}%</td>
          </tr>
        ))}
      </tbody>
    </table>
  );

  return (
    <TarjetaGrafico
      titulo="Productos que asigna CuotaFlex"
      subtitulo="La cuota fija queda para quien no accede a flexibilidad (historial o sobreendeudamiento)"
      grafico={grafico}
      tabla={tabla}
    />
  );
}
