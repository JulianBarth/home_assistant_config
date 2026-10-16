/* SPDX-License-Identifier: BSD-3-Clause */
// Signed power: grid positive = import; battery positive = charging.
const ENERGY_ENTITIES = {
  solar: 'sensor.total_solar_power', grid: 'sensor.grid_power',
  battery: 'sensor.battery_power', home: 'sensor.house_consumption',
  car: 'sensor.wallbox_power', soc: 'sensor.batterie_soc',
  fronius: 'sensor.fronius_solar_power', balcony: 'sensor.balkonkraftwerk_power',
  meter: 'sensor.reading_energy_main_meter', inverter: 'sensor.reading_energy_inverter_ac_output',
  car_raw: 'sensor.wattpilot_charging_power', validity: 'binary_sensor.inverter_data_valid'
};
const esc = value => String(value).replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
class EnergyFlowCard extends HTMLElement {
  constructor() { super(); this.attachShadow({mode:'open'}); }
  setConfig(config) { this.config = {...config, entities:{...ENERGY_ENTITIES, ...config.entities}}; this.signature = ''; this.render(); }
  set hass(hass) {
    this._hass = hass;
    const signature = JSON.stringify(Object.values(this.config?.entities || ENERGY_ENTITIES).map(id => hass.states[id]));
    if (signature !== this.signature) { this.signature = signature; this.render(); }
  }
  getCardSize() { return 9; }
  getGridOptions() { return {columns:12, rows:'auto'}; }
  read(key) {
    const s = this._hass.states[this.config.entities[key]];
    if (!s || !String(s.state).trim() || !Number.isFinite(Number(s.state))) return null;
    return Number(s.state) * (s.attributes?.unit_of_measurement === 'kW' ? 1000 : 1);
  }
  power(n) { if (n === null) return 'Unavailable'; const a = Math.abs(n); return a >= 1000 ? `${(a/1000).toFixed(2)} <small>kW</small>` : `${Math.round(a)} <small>W</small>`; }
  render() {
    if (!this.config || !this._hass) return;
    const v = Object.fromEntries(Object.keys(ENERGY_ENTITIES).map(k => [k, this.read(k)]));
    // Wrapping templates can default to zero: check upstream telemetry as well.
    if (v.meter === null) v.grid = null;
    if (v.car_raw === null) v.car = null;
    if (v.inverter === null || v.fronius === null || this._hass.states[this.config.entities.validity]?.state !== 'on') v.battery = null;
    if (v.fronius === null || v.balcony === null) v.solar = null;
    if ([v.grid,v.inverter,v.car,v.balcony].includes(null)) v.home = null;
    const active = n => n !== null && Math.abs(n) > 5;
    const missing = ['solar','grid','battery','home','car'].filter(k => v[k] === null);
    const load = v.home !== null && v.car !== null ? Math.max(0,v.home) + Math.max(0,v.car) : null;
    const status = missing.length ? 'Some readings unavailable' : v.grid < -5 ? 'Exporting surplus solar' : v.grid > 5 ? 'Drawing from the grid' : 'Locally supplied';
    const icons = {
      solar:'<circle cx="12" cy="12" r="4"/><path d="M12 1v3m0 16v3M1 12h3m16 0h3M4 4l2 2m12 12 2 2M4 20l2-2M18 6l2-2"/>',
      grid:'<path d="M9 3h6l4 18M9 3 5 21M7 10h10M6 16h12M3 7h18M9 3l6 7-8 6 10 5M15 3l-6 7 8 6-10 5"/>',
      battery:'<rect x="3" y="6" width="17" height="12" rx="3"/><path d="M23 10v4M7 10v4m4-4v4m4-4v4"/>',
      home:'<path d="m2 11 10-8 10 8M5 9v12h14V9M9 21v-7h6v7"/>',
      car:'<path d="m4 9 2-5h12l2 5M3 10h18v8H3zM5 18v3m14-3v3M6 13h2m8 0h2"/>'
    };
    const state = key => v[key] === null ? 'Check sensor' : key === 'battery' ? (v.battery > 5 ? 'Charging' : v.battery < -5 ? 'Discharging' : 'Standby') : key === 'grid' ? (v.grid > 5 ? 'Importing' : v.grid < -5 ? 'Exporting' : 'Balanced') : key === 'solar' ? (active(v.solar) ? 'Generating' : 'No generation') : key === 'car' ? (active(v.car) ? 'Charging' : 'Idle') : 'Household only';
    const node = (key,label) => `<button class="node ${key} ${v[key] === null ? 'missing' : ''}" data-key="${key}" aria-label="${label}: ${esc(this.power(v[key]).replace(/<[^>]*>/g,''))}, ${state(key)}"><span class="node-top"><svg viewBox="0 0 24 24" aria-hidden="true">${icons[key]}</svg><span>${label}</span></span><strong>${this.power(v[key])}</strong><span class="node-state">${key === 'battery' && v.soc !== null ? `${Math.round(v.soc)}% · ` : ''}${state(key)}</span>${key === 'battery' ? `<span class="charge-track"><i style="width:${v.soc === null ? 0 : Math.min(100,Math.max(0,v.soc))}%"></i></span>` : ''}</button>`;
    const paths = {solar:'M225 90 C360 90 280 260 420 260',grid:'M225 260 H420',battery:'M225 430 C360 430 280 260 420 260',home:'M420 260 C560 260 510 175 635 175',car:'M420 260 C560 260 510 365 635 365'};
    const drawLines = paths => Object.entries(paths).map(([key,d]) => {
      const reverse = key === 'grid' ? v.grid < 0 : key === 'battery' ? v.battery > 0 : false;
      return `<path class="track" d="${d}"/><path class="flow ${key} ${active(v[key]) ? 'active' : ''} ${reverse ? 'reverse' : ''}" d="${d}" style="stroke-width:${active(v[key]) ? Math.min(9,2+Math.sqrt(Math.abs(v[key]))/14) : 1.5}"/>`;
    }).join('');
    const lines = drawLines(paths);
    const mobileLines = drawLines({solar:'M184 78 H200',grid:'M184 275 H200',battery:'M184 472 H200',home:'M200 177 H216',car:'M200 374 H216'});
    this.shadowRoot.innerHTML = `<style>
      :host{display:block;--solar:#d59619;--grid:#5299de;--battery:#21aa86;--home:#ed8761;--car:#a08ae7;color:var(--primary-text-color,#213631);font-family:var(--paper-font-body1_-_font-family,system-ui,sans-serif)}
      *{box-sizing:border-box}ha-card{display:block;overflow:hidden;border-radius:24px;background:var(--ha-card-background,var(--card-background-color,#fff));border:1px solid var(--divider-color,#e3ebe6);box-shadow:none}
      .content{padding:30px 34px 24px}.eyebrow{font-size:11px;text-transform:uppercase;letter-spacing:2px;color:var(--secondary-text-color,#73857a);font-weight:700}.header{display:flex;justify-content:space-between;align-items:center;gap:16px}h1{font-size:28px;letter-spacing:-1px;font-weight:600;margin:8px 0}.live{font-size:11px;letter-spacing:1px;background:rgba(33,170,134,.1);color:var(--battery);border-radius:30px;padding:8px 12px;white-space:nowrap}.live:before{content:'●';margin-right:7px}.subtitle{font-size:13px;color:var(--secondary-text-color,#73857a);margin:2px 0 0}
      .diagram{position:relative;aspect-ratio:860/510;margin:14px auto 8px;max-width:1000px}.mobile-wires{display:none}.wires,.mobile-wires{position:absolute;width:100%;height:100%;overflow:visible}.track{fill:none;stroke:var(--divider-color,#e6ede8);stroke-width:2}.flow{fill:none;stroke:var(--secondary-text-color,#aeb9b1);opacity:.25}.flow.active{stroke:var(--line);opacity:.8;stroke-dasharray:2 13;stroke-linecap:round;animation:travel 2s linear infinite}.reverse{animation-direction:reverse!important}.solar{--line:var(--solar)}.grid{--line:var(--grid)}.battery{--line:var(--battery)}.home{--line:var(--home)}.car{--line:var(--car)}@keyframes travel{to{stroke-dashoffset:-60}}
      .node{position:absolute;width:24%;height:26%;border:1px solid var(--divider-color,#e2eae4);border-radius:18px;background:var(--ha-card-background,var(--card-background-color,#fff));color:inherit;text-align:left;padding:14px 18px;cursor:pointer;font:inherit;box-shadow:0 5px 20px #142d1c04}.node:hover{border-color:var(--line);box-shadow:0 6px 24px #142d1c0d}.node:focus-visible{outline:3px solid var(--line);outline-offset:3px}.node-top{display:flex;align-items:center;gap:9px;font-size:13px;font-weight:600}.node svg{width:23px;height:23px;stroke:var(--line);fill:none;stroke-width:1.5;stroke-linecap:round;stroke-linejoin:round}.node strong{display:block;font-size:29px;font-weight:550;letter-spacing:-1px;margin-top:10px;font-variant-numeric:tabular-nums}.node small{font-size:14px;font-weight:400;letter-spacing:0;color:var(--secondary-text-color,#73857a)}.node-state{display:block;margin-top:4px;font-size:11px;color:var(--secondary-text-color,#73857a)}.node.solar{left:2%;top:5%}.node.grid{left:2%;top:38%}.node.battery{left:2%;top:71%}.node.home{right:2%;top:22%}.node.car{right:2%;top:59%}.charge-track{position:absolute;height:3px;left:18px;right:18px;top:0;background:var(--divider-color,#e6ede8);border-radius:4px;overflow:hidden}.charge-track i{display:block;height:100%;background:var(--battery)}
      .hub{position:absolute;left:48.84%;top:51%;transform:translate(-50%,-50%);width:100px;height:100px;border-radius:50%;display:grid;place-content:center;text-align:center;border:1px solid var(--divider-color,#e3ebe6);background:var(--ha-card-background,var(--card-background-color,#fff));box-shadow:0 0 0 10px var(--ha-card-background,var(--card-background-color,#fff)),0 0 0 11px var(--divider-color,#e3ebe6)}.hub svg{width:25px;height:25px;margin:auto;stroke:var(--battery);fill:none;stroke-width:1.6}.hub span{font-size:10px;letter-spacing:1px;margin-top:8px;text-transform:uppercase}.footer{display:grid;grid-template-columns:1fr 1fr 1fr;border-top:1px solid var(--divider-color,#e3ebe6);padding-top:20px;gap:16px}.metric span{display:block;font-size:11px;color:var(--secondary-text-color,#73857a);margin-bottom:6px}.metric strong{font-size:17px;font-weight:550}.metric small{font-size:12px;font-weight:400}.note{font-size:11px;color:var(--secondary-text-color,#73857a);margin:20px 0 0;line-height:1.6}.warning{color:var(--error-color,#bd6533);font-size:12px;padding:12px 0 0}.missing strong{font-size:16px;letter-spacing:0}
      @container energy (max-width:600px){.content{padding:22px 16px}.diagram{aspect-ratio:400/580;margin-top:24px}.wires{display:none}.mobile-wires{display:block}.node{width:46%;height:27%;padding:15px}.node.solar{left:0;top:0}.node.grid{left:0;top:34%}.node.battery{left:0;top:68%}.node.home{right:0;top:17%}.node.car{right:0;top:51%}.hub{display:none}.node strong{font-size:27px}.footer{gap:8px}.metric strong{font-size:15px}h1{font-size:25px}.node-state{font-size:12px}}
      :host{container-type:inline-size;container-name:energy}@media(prefers-reduced-motion:reduce){.flow.active{animation:none;stroke-dasharray:none}}
    </style><ha-card><div class="content"><div class="header"><div><div class="eyebrow">Your home · right now</div><h1>${esc(this.config.title || 'Energy in motion')}</h1></div><div class="live">${missing.length ? 'PARTIAL DATA' : 'LIVE POWER'}</div></div><p class="subtitle">${status}</p><div class="diagram"><svg class="wires" viewBox="0 0 860 510" aria-hidden="true">${lines}</svg><svg class="mobile-wires" viewBox="0 0 400 580" aria-hidden="true"><path class="track" d="M200 78 V472"/>${mobileLines}</svg>${node('solar','Solar')}${node('grid','Grid')}${node('battery','Battery')}${node('home','House')}${node('car','Car charger')}<div class="hub"><svg viewBox="0 0 24 24"><path d="m13 2-8 12h7l-1 8 8-12h-7z"/></svg><span>Energy flow</span></div></div><div class="footer"><div class="metric"><span>Total consumption</span><strong>${this.power(load)}</strong></div><div class="metric"><span>Fronius solar</span><strong>${this.power(v.fronius)}</strong></div><div class="metric"><span>Balcony solar</span><strong>${this.power(v.balcony)}</strong></div></div>${missing.length ? `<div class="warning">Unavailable: ${missing.map(esc).join(', ')}. Check sensor details.</div>` : ''}<p class="note">Dots follow the direction of power. Select a device for details.<br>Power in W / kW · Battery power is estimated from the inverter balance.</p></div></ha-card>`;
    this.shadowRoot.querySelectorAll('button[data-key]').forEach(button => button.addEventListener('click', () => this.dispatchEvent(new CustomEvent('hass-more-info',{detail:{entityId:this.config.entities[button.dataset.key]},bubbles:true,composed:true}))));
  }
}
if (!customElements.get('energy-flow-card')) customElements.define('energy-flow-card', EnergyFlowCard);
window.customCards = window.customCards || [];
window.customCards.push({type:'energy-flow-card',name:'Energy in motion',description:'Solar, storage, grid and consumption at a glance.'});
