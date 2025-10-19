import importlib.util
spec = importlib.util.spec_from_file_location('m', 'c:/Users/pinnc/chatpdf-clean/backend/main.py')
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)
print('Imported main.py OK')
