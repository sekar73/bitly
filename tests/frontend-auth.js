// Checks real frontend handlers without depending on SubmitEvent.submitter support.
const fs=require('fs'),vm=require('vm'),assert=require('assert');
const elements={};
function element(id){return elements[id]||(elements[id]={textContent:'',reportValidity:()=>true,querySelectorAll:()=>[],reset:()=>{}})}
const calls=[];
const context={document:{querySelector:element},FormData:class{get(key){return key==='email'?'test@example.com':'testing-password-123'}},
  clearTimeout:()=>{},setTimeout:()=>0,fetch:async(path,options)=>{calls.push({path,options});return {ok:true,status:200,json:async()=>path==='/api/links?offset=0'?[]:{access_token:'test-token',expires_in:1800,user:{email:'test@example.com'}}}}};
vm.createContext(context);
vm.runInContext(fs.readFileSync('app/static/app.js','utf8'),context);
(async()=>{
  await element('#register').onclick();
  assert.strictEqual(calls[0].path,'/api/auth/register');
  assert.strictEqual(JSON.parse(calls[0].options.body).email,'test@example.com');
  calls.length=0;
  await element('#auth').onsubmit({preventDefault:()=>{}});
  assert.strictEqual(calls[0].path,'/api/auth/login');
  element('#auth').reportValidity=()=>false;
  calls.length=0;
  await element('#register').onclick();
  assert.strictEqual(calls.length,0);
  console.log('PASS: registration/login select distinct endpoints without SubmitEvent.submitter; invalid input is not submitted.');
})().catch(e=>{console.error(e);process.exitCode=1});
