class ModelConfig:
    # Initialize the ModelConfig class.
    # This constructor sets up a dictionary 'configs' that stores the configuration settings for different models.
    # Each model's configuration includes an API key, a base URL, the model's name, and a cache seed.
    def __init__(self):
        self.configs = {
            # Configuration settings for the 'gpt - 4o - mini' model.
            # 'api_key' is initially set as an empty string and should be filled with the actual API key.
            # 'base_url' is initially set as an empty string and should be filled with the actual base URL.
            # 'model' specifies the name of the model.
            # 'cache_seed' is used for caching purposes and is set to 42.
            "gpt-4o-mini": {
                "api_key": "",
                "base_url": "",
                "model": "gpt-4o-mini",
                "cache_seed": 42
            },
            # Configuration settings for the 'gpt - 4o - 2024 - 08 - 06' model.
            # Similar to the 'gpt - 4o - mini' model, 'api_key' and 'base_url' are initially empty.
            # 'model' is set to 'gpt - 4o - 2024 - 08 - 06', and 'cache_seed' is 42.
            "gpt-4o-2024-08-06": {
                "api_key": "",
                "base_url": "",
                "model": "gpt-4o-2024-08-06",
                "cache_seed": 42
            },
            # Configuration settings for the 'deepseek - v3' model.
            # 'api_key' and 'base_url' are initially empty.
            # 'model' is set to 'deepseek - v3', and 'cache_seed' is 42.
            "deepseek-v3": {
                "api_key": "",
                "base_url": "",
                "model": "deepseek-v3",
                "cache_seed": 42
            }
        }

    # Retrieve the configuration settings for a given model.
    # Parameters:
    #   model_name (str): The name of the model for which the configuration is to be retrieved.
    # Returns:
    #   dict: The configuration dictionary for the specified model.
    # Raises:
    #   ValueError: If the configuration for the given model name is not found in the 'configs' dictionary.
    def get_config(self, model_name):
        config = self.configs.get(model_name)
        if not config:
            raise ValueError(f"Configuration for model {model_name} not found.")
        return config
