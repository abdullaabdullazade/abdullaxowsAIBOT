def load_prompt(name):
    """
    Loads a prompt template from the 'prompts' directory.

    Parameters:
    - name (str): The name of the prompt file (without .txt extension)

    Returns:
    - str: The contents of the prompt file as a string.
    """
    path = f"prompts/{name}.txt"
    with open(path, "r", encoding="utf-8") as f:
        return f.read()


def format_prompt(template_name, **kwargs):
    """
    Loads a prompt template and formats it using keyword arguments.

    Parameters:
    - template_name (str): Name of the template file (without .txt)
    - **kwargs: Dynamic values to insert into the template

    Returns:
    - str: A fully formatted prompt string, ready to be sent to an AI model.
    """
    template = load_prompt(template_name)
    return template.format(**kwargs)
