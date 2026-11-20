from stk import Stk

from ziglag import invoicing
from ziglag.settings import Config

# Each extension is a package with init_app(app); order is precedence.
extensions = [invoicing]

app = Stk(__name__, config=Config, extensions=extensions)
