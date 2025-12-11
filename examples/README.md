# Examples

In this folder you will find different examples of agents, each with its own prompt to achive a particular type of task.
Using the `tracing.py` script, you can visualize the trace of the execution of the agents in a web interface.

## Environment and configuration

You need to define a `.env` file in the root of your project with the following variables:

```env
GEMINI_API_KEY=your_gemini_api_key
```

## Tracing

For tracing, you can use the `tracing.py` script. It will start a web server and open a browser window with the trace viewer.

```bash
python examples/tracing.py last|trace_id
```

Each example will print the trace id of the iteration. If you use the `last` keyword, it will use the latest trace id.
By default, traces are in json format and will be stored in the `traces` folder of your project.