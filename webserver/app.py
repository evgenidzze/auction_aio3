from aiohttp import web

app = web.Application()

if __name__ == "__main__":
    web.run_app(app, host="0.0.0.0", port=8080)
