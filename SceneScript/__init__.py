import loguru

from SceneScript.register import scripts_manager
from SceneScript.withdraw import (
    single_withdrawal_amount_limit, single_withdrawal_amount_per_time_limit, single_withdrawal_num_per_time_limit,
    project_withdrawal_num_per_time_limit, project_withdrawal_amount_per_time_limit,
    multi_stellar_address_withdraw_to_one,
    single_withdraw_without_recharge
)
from SceneScript.recharge import (
    single_recharge_amount_per_time_limit, single_recharge_amount_limit, single_recharge_num_per_time_limit,
    project_recharge_amount_per_time_limit, project_recharge_num_per_time_limit,
    multi_stellar_address_recharge_to_one,
)

loguru.logger.info('registering')
#                   withdraw
# single
scripts_manager.register(single_withdrawal_amount_limit)
scripts_manager.register(single_withdrawal_amount_per_time_limit)
scripts_manager.register(single_withdrawal_num_per_time_limit)
# project
scripts_manager.register(project_withdrawal_num_per_time_limit)
scripts_manager.register(project_withdrawal_amount_per_time_limit)
# others
scripts_manager.register(multi_stellar_address_withdraw_to_one)
scripts_manager.register(single_withdraw_without_recharge)

#                   recharge
# single
scripts_manager.register(single_recharge_amount_limit)
scripts_manager.register(single_recharge_amount_per_time_limit)
scripts_manager.register(single_recharge_num_per_time_limit)
# project
scripts_manager.register(project_recharge_num_per_time_limit)
scripts_manager.register(project_recharge_amount_per_time_limit)
# others
scripts_manager.register(multi_stellar_address_recharge_to_one)
