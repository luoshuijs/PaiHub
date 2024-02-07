from asyncio import create_subprocess_shell
from typing import Union


async def execute(command: Union[str, bytes], pass_error: bool = True) -> str:
    """Executes command and returns output, with the option of enabling stderr."""
    from asyncio import subprocess

    executor = await create_subprocess_shell(
        command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, stdin=subprocess.PIPE
    )

    stdout, stderr = await executor.communicate()
    if pass_error:
        try:
            result = str(stdout.decode().strip()) + str(stderr.decode().strip())
        except UnicodeDecodeError:
            result = str(stdout.decode("gbk").strip()) + str(stderr.decode("gbk").strip())
    else:
        try:
            result = str(stdout.decode().strip())
        except UnicodeDecodeError:
            result = str(stdout.decode("gbk").strip())
    return result
