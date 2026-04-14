import paddle
print("¿Paddle puede usar GPU?:", paddle.device.is_compiled_with_cuda())
print("¿Hay GPUs disponibles?:", paddle.device.get_device())