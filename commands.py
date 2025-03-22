from command_modules_init import all_commands

overwritten_response = None

def extract_content(response, i):
    """
    Extracts the content inside matching parentheses starting at index i.
    Assumes that response[i:i+3] is a command token and that response[i+3] is '('.
    
    Changes made:
    - Instead of simply finding the next closing parenthesis, we now count nested parentheses.
    - A counter (count) is incremented for each '(' and decremented for each ')'.
    - This ensures that if a command contains nested parentheses (e.g., "prs(shift)"), we correctly
      locate the matching closing parenthesis for the outer command.
    - The function returns a tuple: (extracted content, index of the closing parenthesis).
    """
    if response[i+3] != '(':
        return None, i
    start = i + 4  # start after the opening parenthesis
    count = 1
    j = start
    while j < len(response) and count:
        if response[j] == '(':
            count += 1
        elif response[j] == ')':
            count -= 1
        j += 1
    if count == 0:
        # j is now one past the matching ')', so the content ends at j-1
        return response[start:j-1], j-1
    return None, i

def process_command(response):
    """
    Parse the LLM response for embedded command tokens.
    Schedule actions via add_task and return the cleaned response text and any sound effects.
    """
    clean_response = []
    i = 0
    length = len(response)

    while i < length:
        if response[i:i+3] in all_commands and response[i+3] == '(':
            command = response[i:i+3]
            handler = all_commands[command]
            content, j = extract_content(response, i)
            if content is not None:                    
                method, args = handler(content)
                execute_command(method, args)                
                i = j
        else:
            clean_response.append(response[i])
        i += 1

    r = "".join(clean_response).strip()

    global overwritten_response
    if overwritten_response is not None:
        r = overwritten_response
        overwritten_response = None    

    return r

def execute_command(func, args):
    if (isinstance(args, tuple)):
        func(*args)
    else:
        func(args)

def overwrite_response(new_response):
    global overwritten_response
    overwritten_response = new_response
