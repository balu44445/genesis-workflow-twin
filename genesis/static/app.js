'use strict';
const $ = id => document.getElementById(id);
let snapshot, currentRequest, requestRows = [], latestEvidence, toastTimer, snapshotEpoch = 0, snapshotLoading = true, snapshotLoadSerial = 0;
const labels = {violation: 'Violation found', no_violation_within_bound: 'No violation within bound', inconclusive: 'Inconclusive'};
function el(tag, text, className) { const n = document.createElement(tag); if (text !== undefined) n.textContent = text; if (className) n.className = className; return n; }
function toast(message) { $('toast').textContent = message; $('toast').hidden = false; clearTimeout(toastTimer); toastTimer = setTimeout(() => $('toast').hidden = true, 6500); }
async function api(path, body) {
  const r = await fetch(path, body === undefined ? {} : {method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify(body)});
  const data = await r.json();
  if (!r.ok) { const e = new Error(typeof data.detail === 'string' ? data.detail : 'Check the snapshot and input values.'); e.status = r.status; throw e; }
  return data;
}
function run(id, fn) { $(id).addEventListener('click', async () => { $(id).disabled = true; try { await fn(); } catch(e) { toast(e.message); } finally { $(id).disabled = snapshotLoading && ['verify','explain','compare','create'].includes(id); } }); }
function loadingSnapshot(value) { snapshotLoading = value; ['verify','explain','compare','create'].forEach(id => $(id).disabled = value); }
function choose(select, actors, selected) { select.replaceChildren(...actors.map(a => {const o = el('option', a.name); o.value = a.id; return o;})); if (actors.some(a => a.id === selected)) select.value = selected; }
function loadSnapshot(value) {
  snapshotEpoch++; snapshot = value; latestEvidence = null;
  $('snapshot-json').value = JSON.stringify(value, null, 2);
  $('revision').textContent = value.revision;
  $('source').textContent = value.source.kind === 'fixture' ? 'Synthetic fixture · not a live export' : 'Imported export · provenance must be checked';
  $('distinct').checked = value.policy.require_distinct_approver;
  $('result-label').textContent = 'Not checked'; $('result-bound').textContent = 'Run a fresh check for this snapshot';
  $('verification').replaceChildren(el('p', 'A verification result will appear here, with its snapshot fingerprint and scope.', 'muted'));
  $('comparison').replaceChildren(); $('explanation').hidden = true;
  choose($('requester'), value.actors.filter(a => a.roles.includes('requester')));
  choose($('approver'), value.actors.filter(a => a.roles.includes('approver')), value.actors.find(a => a.name === 'Bob')?.id);
}
function verifyBody() { if(!snapshot || snapshotLoading) throw new Error('Wait for the policy snapshot to finish loading.'); const b = Number($('bound').value), max = Number($('bound').max); if (!Number.isInteger(b) || b < 0 || b > max) throw new Error(`Choose a search depth from 0 to ${max}.`); return {snapshot, bound: b}; }
function renderEvidence(result) {
  latestEvidence = result; $('result-label').textContent = labels[result.status];
  $('result-bound').textContent = `Depth 0–${result.bound} · sequential model`;
  const box = $('verification'); box.replaceChildren(el('p', labels[result.status], 'result-title ' + (result.status === 'violation' ? 'violation' : 'good')));
  box.append(el('p', `Bound ${result.bound}. ${result.scope}`), el('p', `Snapshot SHA-256  ${result.snapshot_sha256}`, 'hash'));
  (result.reasons || []).forEach(reason => box.append(el('p', reason, 'muted')));
  if (result.counterexample) {
    const people = Object.fromEntries(snapshot.actors.map(a => [a.id, a.name]));
    result.counterexample.trace.forEach((t, i) => {const row = el('div', undefined, 'trace-row'); row.append(el('span', String(i + 1).padStart(2, '0')), el('strong', `${people[t.actor] || t.actor} · ${t.action}`), el('span', `${t.before.state} → ${t.after.state}`)); box.append(row);});
    box.append(el('p', `Shortest violation: ${result.shortest_depth} transitions. Concrete replay: ${result.replay.reproduced ? 'matched' : 'not matched'}.`, 'muted'));
  }
}
async function refreshRequests() {
  requestRows = await api('/demo/requests'); $('request-count').textContent = requestRows.length;
  $('request-list').replaceChildren(...requestRows.map(r => {const b = el('button', undefined, 'request-item' + (currentRequest?.id === r.id ? ' selected' : '')); b.append(el('span', r.id.slice(0, 8)), el('span', r.runtime.state)); b.addEventListener('click', () => selectRequest(r.id).catch(e => toast(e.message))); return b;}));
  if (!requestRows.length) $('request-list').append(el('p', 'No requests yet.', 'empty'));
}
async function selectRequest(id) {
  currentRequest = await api('/demo/requests/' + id); renderRequest(); await refreshRequests();
}
function renderRequest() {
  const r = currentRequest, box = $('request-detail'), people = Object.fromEntries(r.snapshot.actors.map(a => [a.id, a.name]));
  box.replaceChildren(el('span', r.runtime.state, 'state'), el('p', `Request ${r.id.slice(0, 8)} · version ${r.version} · ${r.snapshot.revision}`, 'muted small'));
  const meta = el('div', undefined, 'request-meta');
  [['Requester', r.runtime.requester], ['Assigned approver', r.runtime.assigned_approver], ['Approved by', r.runtime.approved_by]].forEach(([label, id]) => {const p = el('div');p.append(el('span', label), el('strong', people[id] || '—'));meta.append(p);}); box.append(meta);
  const label = el('label', 'Act as synthetic user'); label.htmlFor = 'acting-user'; const actor = el('select'); actor.id = 'acting-user';
  const preferred = r.runtime.state === 'pending' ? r.runtime.assigned_approver : r.runtime.state === 'approved' ? r.snapshot.actors.find(a => a.roles.includes('fulfiller'))?.id : r.runtime.requester;
  choose(actor, r.snapshot.actors, preferred); box.append(label, actor);
  const actions = el('div', undefined, 'request-actions');
  ['submit', 'approve', 'fulfill'].forEach(action => { const b = el('button', action[0].toUpperCase() + action.slice(1)); b.addEventListener('click', async () => {
    actions.querySelectorAll('button').forEach(x => x.disabled = true);
    try { await api(`/demo/requests/${r.id}/actions`, {actor: actor.value, action, expected_version: r.version}); }
    catch (e) { toast(e.message); }
    finally { await selectRequest(r.id).catch(e => toast(e.message)); }
  }); actions.append(b); }); box.append(actions, el('p', 'Each action uses this request’s saved policy and version. A conflicting update requires a refresh.', 'small muted'));
  $('timeline-context').textContent = `Request ${r.id.slice(0, 8)} · ${r.snapshot.revision} · synthetic simulation`;
  $('events').replaceChildren(...r.events.map(e => {const li = el('li', undefined, e.outcome === 'rejected' ? 'rejected' : '');const time = el('time', new Date(e.occurred_at).toLocaleString());time.dateTime = e.occurred_at;li.append(el('strong', `${people[e.actor] || 'Unknown actor'} · ${e.action} · ${e.outcome}`), time, el('p', e.reason), el('p', `${e.before_state?.state || 'new'} → ${e.after_state?.state || 'unchanged'} / version ${e.version}`, 'flow'));return li;}));
  $('export-evidence').disabled = false;
}
run('verify', async () => { const epoch=snapshotEpoch; $('explanation').hidden = true; const result=await api('/verify', verifyBody()); if(epoch===snapshotEpoch) renderEvidence(result); });
run('explain', async () => { const epoch=snapshotEpoch; const result = await api('/explain', {...verifyBody(), external_ai: $('external-ai').checked}); if(epoch!==snapshotEpoch)return; renderEvidence(result.evidence);$('explanation').replaceChildren(el('strong', result.explanation.label), el('span', result.explanation.text));$('explanation').hidden = false; });
run('compare', async () => {
  const epoch=snapshotEpoch; const proposed = structuredClone(snapshot); proposed.policy.require_distinct_approver = $('distinct').checked;
  if (proposed.policy.require_distinct_approver !== snapshot.policy.require_distinct_approver) proposed.revision = snapshot.revision.slice(0, 80) + '-preview';
  const c = await api('/compare', {...verifyBody(), proposed}); if(epoch!==snapshotEpoch)return; const box = el('div', undefined, 'comparison-result');
  box.append(el('strong', `${labels[c.current.status]} → ${labels[c.proposed.status]}`));
  const list = el('ul'); c.changes.forEach(change => list.append(el('li', `${change.field}: ${JSON.stringify(change.before)} → ${JSON.stringify(change.after)}`)));box.append(list, el('p', c.note));$('comparison').replaceChildren(box);
});
run('load-snapshot', async () => { const value = JSON.parse($('snapshot-json').value); const result = await api('/verify', {snapshot: value, bound: Number($('bound').value)}); loadSnapshot(value); renderEvidence(result);toast('Synthetic snapshot loaded. Existing requests keep their saved policies.'); });
run('create', async () => {const r = await api('/demo/requests', {snapshot, actor: $('requester').value, assigned_approver: $('approver').value});await selectRequest(r.id);$('requests').scrollIntoView({behavior:'smooth',block:'start'});toast('Synthetic request created. No call was made to ServiceNow.');});
$('example').addEventListener('change', async () => { const serial=++snapshotLoadSerial, epoch=++snapshotEpoch; loadingSnapshot(true); try {const value=await api('/demo/examples/' + $('example').value);if(epoch===snapshotEpoch)loadSnapshot(value);} catch(e) {toast(e.message);if(snapshot)$('example').value=snapshot.policy.require_distinct_approver?'fixed':'vulnerable';} finally {if(serial===snapshotLoadSerial)loadingSnapshot(!snapshot);} });
$('export-evidence').addEventListener('click', () => {if(!currentRequest)return;const blob = new Blob([JSON.stringify({mode:'synthetic_simulation',request:currentRequest},null,2)],{type:'application/json'});const url=URL.createObjectURL(blob);const a=el('a');a.href=url;a.download=`genesis-${currentRequest.id.slice(0,8)}.json`;a.click();setTimeout(()=>URL.revokeObjectURL(url),1000);});
(async () => {loadingSnapshot(true);try { const config = await api('/demo/config'), publicMode=config.mode==='public_synthetic_demo'; $('external-ai').disabled = !config.external_ai_enabled; $('ai-status').textContent = config.external_ai_enabled ? 'Optional external AI is configured. Select the checkbox to send anonymous verifier facts.' : 'External AI is disabled. Local explanations are available.'; $('mode-label').textContent=publicMode?'PUBLIC SYNTHETIC DEMO':'LOCAL DEMO'; $('session-label').innerHTML=publicMode?'Evidence is isolated per visitor and expires.<br>No ServiceNow writes.':'Evidence stays on this computer.<br>No ServiceNow writes.'; $('bound').max=String(config.verification_bound_max); $('bound-range').textContent=`0–${config.verification_bound_max} transitions`; if(Number($('bound').value)>config.verification_bound_max)$('bound').value=String(config.verification_bound_max); loadSnapshot(await api('/demo/examples/fixed'));await refreshRequests();} catch(e) {toast(e.message);} finally {loadingSnapshot(!snapshot);} })();
