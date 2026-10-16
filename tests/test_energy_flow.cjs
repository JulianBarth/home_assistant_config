// Run with: node tests/test_energy_flow.cjs
const {readFileSync}=require('node:fs');
const vm=require('node:vm');
const assert=require('node:assert/strict');
let Card;
const context={HTMLElement:class{attachShadow(){this.shadowRoot={innerHTML:'',querySelectorAll:()=>[],querySelector:()=>null}}},customElements:{get:()=>undefined,define:(name,c)=>{if(name==='energy-flow-card')Card=c}},window:{},console};
vm.runInNewContext(readFileSync('www/energy-flow-card.js','utf8'),context);
const card=new Card();card.setConfig({});
const ids=card.config.entities;
function run(values={}){
 const states={};for(const [key,id] of Object.entries(ids)) states[id]={state:String(values[key]??0),attributes:{unit_of_measurement:'W'}};
 states[ids.validity].state=values.validity??'on'; card.hass={states};return card.shadowRoot.innerHTML;
}
let html=run({solar:4200,fronius:4000,balcony:200,grid:-1000,battery:1200,home:1000,car:1000,soc:70});
assert.match(html,/flow grid active reverse/);assert.match(html,/flow battery active reverse/);assert.match(html,/70% · Charging/);assert.match(html,/Total consumption<\/span><strong>2.00/);
html=run({grid:200,battery:-1000,home:1200,soc:40});
assert.match(html,/flow battery active "/);assert.match(html,/Discharging/);assert.match(html,/flow grid active "/);
html=run();assert.doesNotMatch(html,/class="flow [^"]*active/);assert.match(html,/Standby/);
html=run({fronius:'unavailable',validity:'off'});assert.match(html,/PARTIAL DATA/);assert.match(html,/Unavailable: solar, battery/);assert.doesNotMatch(html,/flow battery active/);
html=run({meter:'unknown',car_raw:'unavailable'});assert.match(html,/Unavailable: grid, home, car/);
run();card._hass.states[ids.grid]={state:'1.5',attributes:{unit_of_measurement:'kW'}};assert.equal(card.read('grid'),1500);
card._hass.states[ids.grid].state='';assert.equal(card.read('grid'),null);
card.setConfig({title:'<img src=x onerror=alert(1)>'});assert.match(card.shadowRoot.innerHTML,/&lt;img/);
console.log('Energy-flow scenarios passed: export, charge, discharge, idle, offline upstream, kW conversion, escaping.');

// Unknown SoC must never appear as an empty battery or a healthy data state.
html=run({soc:'unavailable'});
assert.match(html,/charge-track unknown/);
assert.match(html,/SoC unknown/);
assert.match(html,/live partial/);
assert.match(html,/Unavailable: battery SoC/);
card.setConfig({compact:true});
assert.match(card.shadowRoot.innerHTML,/content compact/);

let StatusCard;
context.customElements.define=(name,c)=>{if(name==='energy-status-card')StatusCard=c};
// Re-evaluate in a fresh context to avoid redeclaring module constants.
const statusContext={...context,customElements:{get:()=>undefined,define:(name,c)=>{if(name==='energy-status-card')StatusCard=c}}};
vm.runInNewContext(readFileSync('www/energy-flow-card.js','utf8'),statusContext);
const summary=new StatusCard();summary.setConfig({});
const states={};
for(const [id,state] of Object.entries({
 'sensor.batterie_soc':'74','sensor.computed_target_soc':'60',
 'sensor.battery_control_mode':'normal','sensor.tibber_cached_energy_prices':'0.123',
 'binary_sensor.tibber_cached_price_data_valid':'on','binary_sensor.grid_control_ready':'on',
 'sensor.grid_connection_status':'grid','input_boolean.battery_automation_on':'on',
 'input_boolean.manual_battery_charge':'off','input_number.manual_charge_target_soc':'85'
}))states[id]={state,attributes:{}};
states['sensor.tibber_cached_energy_prices'].attributes.unit_of_measurement='EUR/kWh';
states['sensor.battery_optimization_data']={state:'60',attributes:{calculation_data:{decision_reason:'Bottom 25%: full target'}}};
summary.hass={states};
assert.match(summary.shadowRoot.innerHTML,/12.3 <small>ct\/kWh/);
assert.match(summary.shadowRoot.innerHTML,/Prices are favorable/);
states['binary_sensor.tibber_cached_price_data_valid'].state='off';summary.hass={states};
assert.doesNotMatch(summary.shadowRoot.innerHTML,/12.3/);
assert.match(summary.shadowRoot.innerHTML,/tag">Unavailable/);
states['sensor.grid_connection_status'].state='island';
states['binary_sensor.grid_control_ready'].state='off';summary.hass={states};
assert.match(summary.shadowRoot.innerHTML,/Island operation/);
assert.match(summary.shadowRoot.innerHTML,/Grid charging is paused/);
states['binary_sensor.grid_control_ready'].state='on';
states['input_boolean.manual_battery_charge'].state='on';summary.hass={states};
assert.match(summary.shadowRoot.innerHTML,/Manual target 85%/);
assert.match(summary.shadowRoot.innerHTML,/Your override/);
states['input_boolean.manual_battery_charge'].state='off';
states['sensor.battery_optimization_data'].attributes.calculation_data.decision_reason='<script>alert(1)</script>';summary.hass={states};
assert.match(summary.shadowRoot.innerHTML,/&lt;script&gt;/);
console.log('Summary scenarios passed: price units and validity, island operation, manual target, escaped decision.');
