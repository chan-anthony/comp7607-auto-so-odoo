"""Rule methods of the sale_email_order models, for offline evaluation scripts.

The rules are methods of the abstract models sale.email.order.authorization and
sale.email.order.disposition. They only use api.model, models.AbstractModel,
tools.ormcache and tools.file_open, so outside Odoo the two model files are loaded
with a minimal stand-in for those names: no Odoo install, database or Docker needed.
Inside an Odoo shell, call the same methods on env['sale.email.order'] instead.
"""
import functools
import importlib.util
import sys
import types
from pathlib import Path

ADDONS = Path(__file__).resolve().parents[1] / 'addons'
MODEL_FILES = ('sale_email_order_authorization', 'sale_email_order_disposition')


def _install_odoo_stand_in():
    if 'odoo' in sys.modules:
        raise RuntimeError("Odoo is loaded: use env['sale.email.order'] rule methods instead of module_rules")
    odoo, tools = types.ModuleType('odoo'), types.ModuleType('odoo.tools')
    tools.ormcache = lambda *keys: functools.cache
    tools.file_open = lambda path, mode='r': open(ADDONS / path, mode, encoding='utf-8')
    odoo.api = types.SimpleNamespace(model=lambda method: method)
    odoo.models = types.SimpleNamespace(AbstractModel=object)
    odoo.tools = tools
    sys.modules.update({'odoo': odoo, 'odoo.tools': tools})


def _load_rules():
    _install_odoo_stand_in()
    classes = []
    for name in MODEL_FILES:
        spec = importlib.util.spec_from_file_location(f'sale_email_order_rules.{name}', ADDONS / 'sale_email_order/models' / f'{name}.py')
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        classes.append(next(v for v in vars(module).values() if isinstance(v, type) and getattr(v, '_name', '').startswith('sale.email.order.')))
    rules = type('SaleEmailOrderRules', tuple(classes), {})()
    rules.env = {cls._name: rules for cls in classes}
    return rules


rules = _load_rules()
