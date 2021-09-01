import loguru

from SceneScript.register import scripts_manager
from SceneScript.withdraw import single_withdrawal_amount_limit, single_withdrawal_amount_per_time_limit
from SceneScript.recharge import single_recharge_amount_per_time_limit, single_recharge_amount_limit

loguru.logger.info('registering')
scripts_manager.register(single_withdrawal_amount_limit)
scripts_manager.register(single_withdrawal_amount_per_time_limit)
scripts_manager.register(single_recharge_amount_limit)
scripts_manager.register(single_recharge_amount_per_time_limit)
