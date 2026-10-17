import ast,asyncio,logging,threading,types,unittest,sys
from pathlib import Path
root=Path(sys.argv.pop(1)) if len(sys.argv)>1 else Path('/config/custom_components/wattpilot')
def functions(file,names,ns):
 tree=ast.parse(file.read_text()); nodes=[n for n in tree.body if isinstance(n,(ast.FunctionDef,ast.AsyncFunctionDef)) and n.name in names]
 exec(compile(ast.Module(body=nodes,type_ignores=[]),str(file),'exec'),ns)
 return ns
class Charger:
 def __init__(self,connected=False,initialized=False,fail=False):
  self.connected=connected; self.allPropsInitialized=initialized; self.fail=fail; self.stopped=False; self.name='test'
 def connect(self):
  if self.fail: raise OSError('connection failed')
 def disconnect(self): self.stopped=True
class SetupTests(unittest.IsolatedAsyncioTestCase):
 async def asyncSetUp(self):
  self.ns={'_LOGGER':logging.getLogger('test'),'CONF_CONNECTION':'connection','CONF_LOCAL':'local','CONF_CLOUD':'cloud','CONF_IP_ADDRESS':'ip_address','CONF_PASSWORD':'password','CONF_SERIAL':'serial','CONF_TIMEOUT':'timeout','DEFAULT_TIMEOUT':15,'asyncio':asyncio,'wattpilot':types.SimpleNamespace()}
  functions(root/'utils.py',{'async_ConnectCharger','async_DisconnectCharger'},self.ns)
 async def connect(self,c): return await self.ns['async_ConnectCharger']('entry',{'timeout':0},c)
 async def test_unreachable_attempt_stops_worker(self):
  c=Charger(); self.assertIs(await self.connect(c),False); self.assertTrue(c.stopped)
 async def test_incomplete_status_stops_worker(self):
  c=Charger(True); self.assertIs(await self.connect(c),False); self.assertTrue(c.stopped)
 async def test_connect_exception_stops_worker(self):
  c=Charger(fail=True); self.assertIs(await self.connect(c),False); self.assertTrue(c.stopped)
 async def test_success_keeps_connection(self):
  c=Charger(True,True)
  self.assertIs(await self.ns['async_ConnectCharger']('entry',{'timeout':1},c),c); self.assertFalse(c.stopped)
 async def test_repeated_failures_release_every_attempt(self):
  cs=[Charger() for _ in range(20)]
  for c in cs: await self.connect(c)
  self.assertTrue(all(c.stopped for c in cs))
class Socket:
 def __init__(self,block=False): self.calls=0; self.entered=threading.Event(); self.closed=threading.Event(); self.block=block
 def run_forever(self):
  self.calls+=1; self.entered.set()
  if self.block: self.closed.wait(2)
 def close(self): self.closed.set()
class WorkerTests(unittest.TestCase):
 def setUp(self):
  file=root/'wattpilot/src/wattpilot/__init__.py'; tree=ast.parse(file.read_text())
  cls=next(n for n in tree.body if isinstance(n,ast.ClassDef) and n.name=='Wattpilot')
  cls.body=[n for n in cls.body if isinstance(n,ast.FunctionDef) and n.name in {'connect','disconnect','_set_disconnected'}]
  ns={'threading':threading,'_LOGGER':logging.getLogger('test'),'RECONNECT_SECONDS':30,'CONST_CONNECTION_SENTINEL':'connection'}
  exec(compile(ast.Module(body=[cls],type_ignores=[]),str(file),'exec'),ns)
  self.c=ns['Wattpilot'](); self.c._wst=threading.Thread(); self.c._wsapp=Socket(); self.c._property_callback=None
 def tearDown(self): self.c.disconnect(); self.c._wst.join(2)
 def test_close_interrupts_backoff(self):
  self.c.connect(); self.assertTrue(self.c._wsapp.entered.wait(1)); self.c.disconnect(); self.c._wst.join(1); self.assertFalse(self.c._wst.is_alive())
 def test_duplicate_connect_does_not_spawn_second_worker(self):
  self.c._wsapp=Socket(True); self.c.connect(); self.assertTrue(self.c._wsapp.entered.wait(1)); worker=self.c._wst; self.c.connect(); self.assertIs(worker,self.c._wst); self.assertEqual(self.c._wsapp.calls,1)
 def test_socket_shutdown_stops_worker(self):
  self.c._wsapp=Socket(True); self.c.connect(); self.assertTrue(self.c._wsapp.entered.wait(1)); self.c.disconnect(); self.c._wst.join(1); self.assertFalse(self.c._wst.is_alive()); self.assertFalse(self.c._connected)
if __name__=='__main__':
 logging.disable(logging.CRITICAL); unittest.main(verbosity=2)
