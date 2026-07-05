"""Register all built-in HaxJobs agent tools.

Importing this module triggers register() side-effects in each domain
module.  Callers that need specific functions should import from the
domain modules directly (e.g. from haxjobs.agent.tools_profile import
profile_read).
"""
from haxjobs.agent import tools_db as tools_db  # noqa: F401
from haxjobs.agent import tools_product as tools_product  # noqa: F401
from haxjobs.agent import tools_profile as tools_profile  # noqa: F401
from haxjobs.agent import tools_web as tools_web  # noqa: F401
