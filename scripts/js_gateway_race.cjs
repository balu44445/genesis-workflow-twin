// Controlled interleavings against the real gateway/guard source; not a PDI database test.
const fs = require('node:fs'), vm = require('node:vm'), assert = require('node:assert/strict');
const ids = {alice:'1'.repeat(32),bob:'2'.repeat(32),carol:'3'.repeat(32)}, record='4'.repeat(32);
const copy = x => JSON.parse(JSON.stringify(x));
let db, actor, hook, requestWriteFails, claimWriteFails;
let manifest = JSON.parse(fs.readFileSync('examples/fixed.json','utf8'));
manifest.actors.forEach(a=>a.id=ids[a.id]);
manifest.source={kind:'servicenow_export',description:'Configured GENESIS PDI sample; not inferred platform behavior'};
function reset() {
  actor=ids.bob; hook=null;requestWriteFails=false;claimWriteFails=false;
  db={sys_dictionary:[{name:'u_genesis_action_claim',element:'u_key',unique:'true'}],
      sys_user:Object.values(ids).map(sys_id=>({sys_id,active:'true'})),
      sys_user_has_role:Object.values(ids).map(user=>({user,'role.name':'u_genesis_demo'})),
      u_genesis_action_claim:[],u_genesis_request:[{sys_id:record,u_snapshot:JSON.stringify(manifest),u_state:'pending',u_requester:ids.alice,u_assigned_approver:ids.bob,u_approved_by:''}]};
}
class GlideRecord {
  constructor(table){this.table=table;this.filters=[];this.rows=[];this.index=-1;this.row={};}
  isValid(){return !!db[this.table];}
  initialize(){this.row={};}
  addQuery(k,v){this.filters.push([k,v]);}
  setLimit(){}
  query(){this.rows=(db[this.table]||[]).filter(r=>this.filters.every(([k,v])=>r[k]===v));}
  next(){if(++this.index>=this.rows.length)return false;this.row=copy(this.rows[this.index]);return true;}
  get(id){const r=(db[this.table]||[]).find(r=>r.sys_id===id);if(!r)return false;this.row=copy(r);return true;}
  getValue(k){return this.row[k]??null;}
  setValue(k,v){this.row[k]=v;}
  insert(){
    if(this.table==='u_genesis_action_claim'&&db[this.table].some(r=>r.u_key===this.row.u_key))return null;
    this.row.sys_id='claim'+db[this.table].length;db[this.table].push(copy(this.row));
    if(hook){const f=hook;hook=null;f();}return this.row.sys_id;
  }
  update(){
    if(this.table==='u_genesis_request'&&requestWriteFails)return null;
    if(this.table==='u_genesis_action_claim'&&claimWriteFails)return null;
    const i=db[this.table].findIndex(r=>r.sys_id===this.row.sys_id);if(i<0)return null;
    db[this.table][i]=copy(this.row);return this.row.sys_id;
  }
}
const ctx=vm.createContext({Class:{create:()=>function(){if(this.initialize)this.initialize.apply(this,arguments);}},GlideRecord,gs:{hasRole:()=>true,getUserID:()=>actor,getProperty:()=>JSON.stringify(manifest)}});
for(const name of ['GenesisCore','GenesisGuard','GenesisGateway'])vm.runInContext(fs.readFileSync(`servicenow/${name}.js`,'utf8'),ctx);
const act=action=>new ctx.GenesisGateway().act(record,action);
let tests=[];
reset();let competitorRejected=false;
hook=()=>{try{act('approve');}catch(e){competitorRejected=true;}};
assert.equal(act('approve').runtime.state,'approved');assert(competitorRejected);
assert.equal(db.u_genesis_action_claim.length,1);assert.equal(db.u_genesis_action_claim[0].u_outcome,'applied');
assert.throws(()=>act('approve'));actor=ids.carol;assert.equal(act('fulfill').runtime.state,'fulfilled');
assert.equal(db.u_genesis_action_claim.length,2);tests.push('one winner per stage under overlapping approvals; later fulfillment succeeds');
reset();requestWriteFails=true;assert.throws(()=>act('approve'));requestWriteFails=false;
assert.throws(()=>act('approve'));assert.equal(db.u_genesis_request[0].u_state,'pending');assert.equal(db.u_genesis_action_claim.length,1);
tests.push('failed state write leaves permanent claim and blocks unsafe retry');
reset();claimWriteFails=true;assert.throws(()=>act('approve'));assert.equal(db.u_genesis_request[0].u_state,'approved');
assert.equal(db.u_genesis_action_claim[0].u_outcome,'claimed');assert.throws(()=>act('approve'));
tests.push('uncertain claim completion never permits repeated approval');
reset();db.sys_dictionary[0].unique='false';assert.throws(()=>act('approve'));
assert.equal(db.u_genesis_action_claim.length,0);assert.equal(db.u_genesis_request[0].u_state,'pending');
tests.push('missing uniqueness setting fails closed');
reset();hook=()=>{db.u_genesis_request[0].u_assigned_approver=ids.carol;};assert.throws(()=>act('approve'));
assert.equal(db.u_genesis_request[0].u_state,'pending');tests.push('changed persisted state after claim is rejected');
reset();actor=ids.alice;assert.throws(()=>act('approve'));assert.equal(db.u_genesis_action_claim.length,0);
tests.push('unauthorized action cannot consume stage claim');
console.log(JSON.stringify({mode:'mocked_storage_interleavings',passed:tests,live_pdi_tested:false}));
