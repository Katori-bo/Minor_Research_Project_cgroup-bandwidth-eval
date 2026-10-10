// Execute only the inspected numeric/parser portions of the pinned viewers.
// No UI, server, network request, runtime sampler, or profiler is started.
const fs = require('fs');
const vm = require('vm');
const path = require('path');
const root = path.resolve(__dirname, '..');
const out = path.join(root, 'analysis/runtime_io_profiler_semantics_gate/20261008');
const inputs = JSON.parse(fs.readFileSync(path.join(out, 'reporting_inputs.json'), 'utf8'));
let results = [];
for (const name of ['coz', 'bcoz']) {
  const file = path.join(out, 'sources', name, 'viewer/js/profile.js');
  const source = fs.readFileSync(file, 'utf8');
  const helpers = source.slice(source.indexOf('function isValidDataPoint('), source.indexOf('function max_normalized_area('));
  let body;
  if (name === 'coz') {
    body = source.slice(source.indexOf('class Profile {'), source.indexOf('    drawLegend() {')) + '\n}\n';
  } else {
    body = source.slice(source.indexOf('var Profile ='), source.indexOf('    Profile.prototype.drawLegend =')) + '\nreturn Profile; }());\n';
  }
  if (!helpers || !body || !body.includes('getSpeedupData')) throw new Error('source extraction failed');
  for (const record of inputs.records) {
    const sandbox = {input: record.profile_text};
    vm.createContext(sandbox);
    vm.runInContext('const MIN_DELTA=5;\n' + helpers + body + `
      const warnings=[];
      const profile=new Profile(input,null,null,()=>2,(...args)=>warnings.push(args));
      output={results:profile.getSpeedupData(2),warnings:warnings};
    `, sandbox, {timeout: 1000});
    if (sandbox.output.warnings.length) throw new Error('unexpected viewer warning');
    results.push({profiler:name,id:record.id,...sandbox.output});
  }
}
fs.writeFileSync(path.join(out, 'native_reporting_results.json'),JSON.stringify({
  scope:'Pinned native parser/aggregation/reporting code on declared synthetic profiles; runtime profiler not executed.',
  results:results
}, null, 2)+'\n');
console.log(JSON.stringify({native_reporting_records:results.length,runtime_profiler_executed:false}));
