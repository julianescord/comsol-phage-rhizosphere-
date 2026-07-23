% build_rhizosphere_model.m
%
% Esqueleto de script LiveLink for MATLAB para construir el modelo de
% liberacion controlada en la rizosfera descrito en:
%   ../docs/especificacion_tecnica.md
%
% IMPORTANTE - LEE ESTO ANTES DE USAR:
% Este script NO ha sido probado contra COMSOL (no hay ninguna instalacion
% en este equipo). Los nombres de metodos, tags de fisica ('tds', etc.) y
% nombres de propiedades pueden variar segun tu version de COMSOL.
%
% Forma mas confiable de obtener el codigo exacto y correcto:
%   1. Construye el modelo UNA VEZ manualmente en COMSOL Desktop siguiendo
%      la especificacion tecnica.
%   2. File > Save As > elige "Model File for MATLAB (*.m)".
%   3. COMSOL genera automaticamente el script LiveLink exacto para TU
%      version, con los tags y metodos correctos.
% Usa este esqueleto como mapa conceptual de los pasos, y el archivo
% generado por COMSOL como fuente de verdad para la sintaxis exacta.

import com.comsol.model.*
import com.comsol.model.util.*

model = ModelUtil.create('RhizosphereReleaseModel');
model.modelNode.create('comp1');

%% 1. Parametros (ver tabla en especificacion_tecnica.md, seccion 6)
% Reemplazar cada valor placeholder por datos propios o de literatura.
p = model.param;
p.set('D_soil',   '1e-10[m^2/s]', 'Coef. difusion efectivo en suelo');
p.set('eps_soil', '0.45',         'Porosidad del suelo');
p.set('Kd',       '1e-3[m^3/kg]', 'Coef. de sorcion lineal');
p.set('k_deg',    '1e-6[1/s]',    'Constante de degradacion');
p.set('Vmax_root','1e-8[mol/(m^2*s)]', 'Captacion radicular maxima');
p.set('Km_root',  '1e-3[mol/m^3]', 'Constante de Michaelis-Menten radicular');
p.set('r_capsule','2[mm]',        'Radio de la capsula de liberacion');
p.set('r_rhizo',  '10[mm]',       'Radio externo de la zona rizosferica');
p.set('r_domain', '50[mm]',       'Radio externo del dominio de suelo');
p.set('t_end',    '30[d]',        'Horizonte de simulacion');

%% 2. Geometria axisimetrica (capsula -> rizosfera -> bulk soil)
geom = model.component('comp1').geom.create('geom1', 2);
geom.axisymmetric(true);

% Dominio 1: capsula (o, si se usa la funcion de entrada empirica de la
% seccion 5 de la especificacion, este dominio puede omitirse y
% reemplazarse directamente por una condicion de frontera de flujo).
geom.create('capsule', 'Circle');
geom.feature('capsule').set('r', 'r_capsule');

% Dominio 2: anillo de rizosfera
geom.create('rhizo', 'Circle');
geom.feature('rhizo').set('r', 'r_rhizo');

% Dominio 3: suelo a granel
geom.create('bulk', 'Circle');
geom.feature('bulk').set('r', 'r_domain');

geom.run;
% NOTA: en la GUI, tras crear los circulos concentricos se usa
% "Form Union" (o "Form Assembly" si se necesitan discontinuidades) para
% fusionar los dominios en una sola geometria, igual que en el paper de
% referencia (seccion 2.6 del PDF).

%% 3. Fisica: Transport of Diluted Species in Porous Media
% Tag de interfaz e identificador de tipo a verificar contra tu version;
% en versiones recientes suele ser 'tds' / 'DilutedSpeciesInPorousMedia'.
physicsTag = 'tds';
tds = model.component('comp1').physics.create(physicsTag, ...
    'DilutedSpeciesInPorousMedia', 'geom1');

% Propiedades de transporte por dominio (rizosfera vs. bulk soil pueden
% diferir en porosidad/difusividad si hay actividad radicular).
% tds.feature('pm1').set('D_c', {'D_soil'; '0'; '0'; '0'; 'D_soil'; '0'; '0'; '0'; 'D_soil'});
% tds.feature('pm1').set('epsilon_p', 'eps_soil');

%% 4. Reacciones: sorcion + degradacion
% Nodo de reaccion (isoterma lineal + degradacion de primer orden).
% rxn = tds.feature.create('reac1', 'Reactions', 2);
% rxn.set('R_c', '-k_deg*c - Kd*c');   % placeholder; ajustar segun
%                                       % isoterma elegida (lineal/
%                                       % Freundlich/Langmuir).

%% 5. Condicion de frontera: liberacion desde la capsula
% Funcion de liberacion empirica C_H(t) ajustada a datos in vitro propios
% (ver especificacion_tecnica.md, seccion 5). Ejemplo con funcion
% analitica; reemplazar por 'Interpolation' si los datos son tabulares.
fn = model.func.create('release_fn', 'Analytic');
fn.set('expr', 'C0*exp(-t/tau)');   % PLACEHOLDER - reemplazar por el
                                     % ajuste real a los datos de
                                     % liberacion del sistema propio.
fn.set('args', {'t'});

% inflow = tds.create('inflow1', 'FluxBoundary', 1);
% inflow.selection.set([]);  % seleccionar frontera capsula-rizosfera
% inflow.set('N0', 'release_fn(t)');

%% 6. Sumidero radicular (Michaelis-Menten)
% root_sink = tds.create('rootuptake1', 'FluxBoundary', 1);
% root_sink.selection.set([]);  % seleccionar frontera radicular
% root_sink.set('N0', '-Vmax_root*c/(Km_root+c)');

%% 7. Mallado (refinar en interfaces con gradientes fuertes)
mesh = model.component('comp1').mesh.create('mesh1');
mesh.autoMeshSize(4);  % 'Normal' aprox.; refinar manualmente cerca de
                        % la frontera capsula-rizosfera y la superficie
                        % radicular una vez validada la geometria.
mesh.run;

%% 8. Estudio time-dependent
std1 = model.study.create('std1');
time = std1.create('time', 'Transient');
time.set('tlist', 'range(0,t_end/100,t_end)');
std1.run;

%% 9. Guardar modelo y exportar resultados
model.save('rhizosphere_release_model.mph');
% Post-procesamiento: exportar curvas de concentracion en la superficie
% radicular y en el borde de la rizosfera (ver especificacion_tecnica.md,
% seccion 9) via model.result.export.
