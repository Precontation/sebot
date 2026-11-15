import discord
import dotenv
import os
import asyncio
from openai import AsyncOpenAI, APIStatusError
from openai.types.chat import ChatCompletionMessageParam

dotenv.load_dotenv()

# Discord stuff
intents = discord.Intents.default()
intents.message_content = True

discord_client = discord.Client(
    intents=intents,
    allowed_mentions=discord.AllowedMentions(
        users=True, roles=False, everyone=False, replied_user=True
    ),
)
tree = discord.app_commands.CommandTree(discord_client)

# Modal AI stuff
MODAL_BEARER_TOKEN = os.environ["MODAL_BEARER_TOKEN"]
MODAL_URL = os.environ["MODAL_URL"]

modal_client = AsyncOpenAI(
    base_url=f"{MODAL_URL}/v1",
    api_key=MODAL_BEARER_TOKEN,
)

# Consts
SYSTEM_PROMPT = "You're name is Sebot."
ERROR_MESSAGE = "An error occurred :("
ASSISTANT_MESSAGE_PREFIX = "Sebot: "
OWNER_USER_IDS = [766046835109789716, 1004100811481170010]
MAX_CONTEXT_MESSAGES = 5
AI_MODEL = "Precontation/sebot-w4a16"


async def get_ai_message(formatted_messages: list[ChatCompletionMessageParam]):
    try:
        formatted_prompt: ChatCompletionMessageParam = {
            "role": "system",
            "content": SYSTEM_PROMPT,
        }

        messages: list[ChatCompletionMessageParam] = [
            formatted_prompt
        ] + formatted_messages

        completion = await asyncio.wait_for(
            modal_client.chat.completions.create(
                model=AI_MODEL,
                messages=messages,
                temperature=0.6,
                max_completion_tokens=100,
                top_p=1,
                stream=False,
                extra_body={"chat_template_kwargs": {"enable_thinking": False}},
            ),
            timeout=60,
        )
    except APIStatusError as e:
        if e.status_code == 503:
            print("Model is waking up...")
            return "Waking up... try again in a min or two :3"

        print(f"Modal failed! HTTP {e.status_code}: {e}")
        return ERROR_MESSAGE

    except Exception as e:
        print(f"Modal failed! Error: {e}")
        return ERROR_MESSAGE

    if len(completion.choices) != 0 and completion.choices[0].message.content:
        return completion.choices[0].message.content
    else:
        return ERROR_MESSAGE


@discord_client.event
async def on_ready():
    await tree.sync()
    print(f"Bot is logged in and ready!")


@discord_client.event
async def on_message(message: discord.Message):
    if not (
        (discord_client.user in message.mentions or message.guild is None)
        and message.author != discord_client.user
    ):
        return

    async with message.channel.typing():
        messages: list[discord.Message] = []
        messages = [
            m async for m in message.channel.history(limit=MAX_CONTEXT_MESSAGES)
        ]
        messages.reverse()  # Reverse it to make it chronological now

        formattedMessages: list[ChatCompletionMessageParam] = []

        for m in messages:
            content = m.author.display_name + ": " + m.clean_content
            if m.author == discord_client.user:
                if m.clean_content == ERROR_MESSAGE:
                    continue  # Don't have it knowing it errored!

                formattedMessages.append(
                    {
                        "role": "assistant",
                        "content": content.removeprefix(
                            ASSISTANT_MESSAGE_PREFIX
                        ),  # Remove so the AI doesn't bug out and go insane
                    }
                )
            else:
                formattedMessages.append({"role": "user", "content": content})

        message_response = await get_ai_message(formattedMessages)
        await message.reply(message_response[:2000])


@tree.command(name="ask", description="Ask Sebot a question")
@discord.app_commands.allowed_contexts(guilds=True, dms=True, private_channels=True)
@discord.app_commands.allowed_installs(guilds=True, users=True)
async def ask(interaction: discord.Interaction, question: str):
    await interaction.response.defer()

    message_response = await get_ai_message([{"role": "user", "content": question}])

    await interaction.followup.send(
        f"{interaction.user.display_name}: {question}\n{ASSISTANT_MESSAGE_PREFIX}{message_response}"[
            :2000
        ]
    )


discord_client.run(os.environ["DISCORD_BOT_TOKEN"])
