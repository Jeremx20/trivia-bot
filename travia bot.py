import discord
from discord.ext import commands, tasks
import requests
import random
import asyncio
import html
import json

# Bot setup
TOKEN = "MTM1MTI1Mjg3NjU1ODYwMjI0MA.GgpwHR.KbrXDIAjsX_nHifSTTMprglAAG-gJf3P0uu0n0"
intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)

# Variables globales pour stocker la question et les réponses
current_question = None
current_answers = None
current_correct_answer = None
current_category = None

# Load or initialize scores
def load_scores():
    try:
        with open("scores.json", "r") as f:
            return json.load(f)
    except FileNotFoundError:
        return {}

def save_scores(scores):
    with open("scores.json", "w") as f:
        json.dump(scores, f, indent=4)

scores = load_scores()

# Fetch trivia question
def get_trivia():
    global current_question, current_answers, current_correct_answer, current_category
    url = "https://opentdb.com/api.php"
    params = {"amount": 1, "category": 9, "difficulty": "medium", "type": "multiple"}
    response = requests.get(url, params=params)
    data = response.json()
    
    if data.get("response_code") == 0:
        current_question = html.unescape(data["results"][0]["question"])
        current_correct_answer = html.unescape(data["results"][0]["correct_answer"])
        incorrect_answers = [html.unescape(ans) for ans in data["results"][0]["incorrect_answers"]]
        current_answers = incorrect_answers + [current_correct_answer]
        random.shuffle(current_answers)
        current_category = data["results"][0]["category"]
        return current_question, current_answers, current_correct_answer, current_category
    return None, None, None, None

# Post trivia question at a set interval (every hour)
@tasks.loop(hours=1)  # Définit l'intervalle, ici toutes les heures
async def post_trivia():
    channel = bot.get_channel(1351247180744102013)  # Remplace par l'ID de ton canal
    question, answers, correct_answer, category = get_trivia()
    if question:
        options = "\n".join([f"{i+1}. {answer}" for i, answer in enumerate(answers)])
        trivia_message = await channel.send(f"**Question:** {question}\n**Options:**\n{options}")
        
        # Wait for an answer in the same channel
        def check(m):
            return m.author != bot.user and m.channel == channel and m.content.isdigit()

        try:
            answer = await bot.wait_for("message", check=check, timeout=30)
            answer_choice = int(answer.content)
            if answer_choice < 1 or answer_choice > len(answers):
                await channel.send("❌ Invalid choice. Please select a number between 1 and 4.")
                return

            if answers[answer_choice - 1] == correct_answer:
                # Update the score
                scores[answer.author.name] = scores.get(answer.author.name, 0) + 1
                save_scores(scores)
                await channel.send(f"🎉 Correct, {answer.author.name}! You now have {scores[answer.author.name]} points.")
            else:
                await channel.send(f"❌ Wrong! The correct answer was: **{correct_answer}**")
        except asyncio.TimeoutError:
            await channel.send(f"⌛ Time's up! The correct answer was: **{correct_answer}**")

# Trivia command
@bot.command()
async def trivia(ctx):
    question, answers, correct_answer, category = get_trivia()
    if question:
        options = "\n".join([f"{i+1}. {answer}" for i, answer in enumerate(answers)])
        await ctx.send(f"**Question:** {question}\n**Options:**\n{options}")
        
        def check(m):
            return m.author == ctx.author and m.channel == ctx.channel and m.content.isdigit()
        
        try:
            answer = await bot.wait_for("message", check=check, timeout=30)
            answer_choice = int(answer.content)
            if answer_choice < 1 or answer_choice > len(answers):
                await ctx.send("❌ Invalid choice. Please select a number between 1 and 4.")
                return

            if answers[answer_choice - 1] == correct_answer:
                # Update the score
                scores[ctx.author.name] = scores.get(ctx.author.name, 0) + 1
                save_scores(scores)
                await ctx.send(f"🎉 Correct, {ctx.author.name}! You now have {scores[ctx.author.name]} points.")
            else:
                await ctx.send(f"❌ Wrong! The correct answer was: **{correct_answer}**")
        except asyncio.TimeoutError:
            await ctx.send(f"⌛ Time's up! The correct answer was: **{correct_answer}**")

# Leaderboard command
@bot.command()
async def leaderboard(ctx):
    if not scores:
        await ctx.send("No scores yet!")
    else:
        sorted_scores = sorted(scores.items(), key=lambda x: x[1], reverse=True)
        leaderboard_text = "\n".join([f"{i+1}. {name} - {score} points" for i, (name, score) in enumerate(sorted_scores, 0)])
        await ctx.send(f"🏆 **Leaderboard:**\n{leaderboard_text}")

# Hint command with 3 types of hints
@bot.command()
async def hint(ctx, hint_type: int = None):
    if hint_type is None:
        await ctx.send("❌ You must specify a hint type. Please use `!hint 1`, `!hint 2`, or `!hint 3`.")
        return

    if current_question is None or current_answers is None or current_correct_answer is None:
        await ctx.send("❌ No question is currently active. Please wait for the next trivia question.")
        return

    if hint_type == 1:
        # Hint type 1: Category hint
        await ctx.send(f"💡 **Hint 1:** The category of this question is: **{current_category}**")
    elif hint_type == 2:
        # Hint type 2: Partial answer hint (revealing first letter)
        await ctx.send(f"💡 **Hint 2:** The correct answer starts with: **{current_correct_answer[0]}**")
    elif hint_type == 3:
        # Hint type 3: Incorrect answer explanation
        incorrect_answer = random.choice([answer for answer in current_answers if answer != current_correct_answer])
        await ctx.send(f"💡 **Hint 3:** One of the incorrect answers is: **{incorrect_answer}**. It is incorrect because it doesn't relate to the question.")
    else:
        await ctx.send("❌ Invalid hint type. Please choose 1, 2, or 3.")

# Start the loop when the bot is ready
@bot.event
async def on_ready():
    print(f"Logged in as {bot.user}")
    post_trivia.start()  # Démarre la boucle lorsque le bot est prêt

# Run bot
bot.run(TOKEN)
