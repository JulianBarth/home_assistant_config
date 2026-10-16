// Run with: node tests/test_energy_flow.cjs
const {readFileSync}=require('node:fs');
const vm=require('node:vm');
const assert=require('node:assert/strict');
let Card;
const context={HTMLElement:class{attachShadow(){this.shadowRoot={innerHTML:'',querySelectorAll:()=>[]}}},customElements:{get:()=>undefined,define:(_,c)=>Card=c},window:{},console};
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
