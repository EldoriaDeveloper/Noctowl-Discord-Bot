import discord
from discord.ext import commands, tasks
from discord import app_commands
import random, globals

OWNER_ID = 412292524556943363 ## OWNER ID
CATEGORY_ID = 1423196729393811466  # 🔹 Replace with your #category id
SPAWN_INTERVAL = 20
TOTAL_QUESTIONS = 100

user_scores = {}
user_answers = {}
validation_status = {}  # Track validation status: {user_id: {answer_index: "correct"/"wrong"/None}}

def get_random_spawn_time():
    return random.randint(1800, 3600) # 30 Minutes - 1 Hour

async def fetch_channels_from_category(bot):
    try:
        category = bot.get_channel(CATEGORY_ID)
        if category is None or not isinstance(category, discord.CategoryChannel):
            globals.log_message(error=f"Category with ID {CATEGORY_ID} not found or is not a category")
            return []
        
        # Get all text channels in the category
        text_channels = [channel for channel in category.channels if isinstance(channel, discord.TextChannel)]
        globals.log_message(message=f"[HarperBot] Found {len(text_channels)} text channels in category")
        return text_channels
        
    except Exception as e:
        globals.log_message(error=e)
        return []

class QuestionModal(discord.ui.Modal, title="Harper Question Response"):
    def __init__(self, question: dict):
        super().__init__(timeout=None)
        self.question_text = question["question"]
        self.id = question["id"]

        self.answer = discord.ui.TextInput(
            label="Your Answer",
            style=discord.TextStyle.paragraph,
            placeholder="Write your solution here...",
            required=True,
            max_length=500  # Changed from 1000 to 500
        )
        self.add_item(self.answer)

    async def on_submit(self, interaction: discord.Interaction):
        try:
            await interaction.response.send_message(
                f"✅ Thanks for your response, {interaction.user.mention}!", 
                ephemeral=True
            )

            # Initialize user data if not exists
            if interaction.user.id not in user_answers:
                user_answers[interaction.user.id] = []
            if interaction.user.id not in user_scores:
                user_scores[interaction.user.id] = 0
            if interaction.user.id not in validation_status:
                validation_status[interaction.user.id] = {}

            user_answers[interaction.user.id].append({
                "id": self.id,
                "question": self.question_text,
                "answer": self.answer.value
            })
            
            # Mark as not validated
            answer_index = len(user_answers[interaction.user.id])
            validation_status[interaction.user.id][answer_index] = None

            view = discord.ui.View.from_message(interaction.message)
            for item in view.children:
                item.disabled = True
            await interaction.message.edit(view=view)
        
            globals.log_message(message=f"[HarperBot] {interaction.user} answered question ID {self.id}: {self.answer.value}")
        except Exception as e:
            globals.log_message(error=e)


class ValidationView(discord.ui.View):
    def __init__(self, user_id: int, answer_index: int):
        super().__init__(timeout=180)
        self.user_id = user_id
        self.answer_index = answer_index
        self.validated = False

    @discord.ui.button(label="✅ Correct", style=discord.ButtonStyle.success, row=0)
    async def correct_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        if self.validated:
            await interaction.response.send_message("❌ This answer has already been validated!", ephemeral=True)
            return

        # Show point selection view
        point_view = PointSelectionView(self.user_id, self.answer_index, self)
        await interaction.response.send_message(
            "**Select points to award (2-5):**",
            view=point_view,
            ephemeral=True
        )

    @discord.ui.button(label="❌ Wrong", style=discord.ButtonStyle.danger, row=0)
    async def wrong_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        if self.validated:
            await interaction.response.send_message("❌ This answer has already been validated!", ephemeral=True)
            return

        # Give 1 point for wrong answers
        user_scores[self.user_id] = user_scores.get(self.user_id, 0) + 1
        self.validated = True
        
        # Update validation status
        if self.user_id not in validation_status:
            validation_status[self.user_id] = {}
        validation_status[self.user_id][self.answer_index] = "wrong"
        
        user = interaction.guild.get_member(self.user_id)
        username = user.display_name if user else f"User {self.user_id}"
        
        await interaction.response.send_message(
            f"❌ Answer marked as **wrong**. {username} receives **1 point** for attempting. Total: **{user_scores[self.user_id]}** points.",
            ephemeral=False
        )
        
        # Disable buttons after validation
        for item in self.children:
            item.disabled = True
        await interaction.message.edit(view=self)
        
        globals.log_message(message=f"[HarperBot] {interaction.user} marked answer {self.answer_index} as wrong for user {self.user_id} - 1 point awarded")


class PointSelectionView(discord.ui.View):
    def __init__(self, user_id: int, answer_index: int, parent_view: ValidationView):
        super().__init__(timeout=60)
        self.user_id = user_id
        self.answer_index = answer_index
        self.parent_view = parent_view

    @discord.ui.button(label="2 Points", style=discord.ButtonStyle.primary)
    async def two_points(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.award_points(interaction, 2)

    @discord.ui.button(label="3 Points", style=discord.ButtonStyle.primary)
    async def three_points(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.award_points(interaction, 3)

    @discord.ui.button(label="4 Points", style=discord.ButtonStyle.primary)
    async def four_points(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.award_points(interaction, 4)

    @discord.ui.button(label="5 Points", style=discord.ButtonStyle.primary)
    async def five_points(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.award_points(interaction, 5)

    async def award_points(self, interaction: discord.Interaction, points: int):
        user_scores[self.user_id] = user_scores.get(self.user_id, 0) + points
        self.parent_view.validated = True
        
        # Update validation status
        if self.user_id not in validation_status:
            validation_status[self.user_id] = {}
        validation_status[self.user_id][self.answer_index] = "correct"
        
        user = interaction.guild.get_member(self.user_id)
        username = user.display_name if user else f"User {self.user_id}"
        
        # Send public message in the channel where validation started
        channel = interaction.channel
        await channel.send(
            f"✅ Answer marked as **correct**! {username} receives **{points} points**. Total: **{user_scores[self.user_id]}** points."
        )
        
        # Respond to the ephemeral interaction
        await interaction.response.send_message(
            f"✅ Successfully awarded **{points} points** to {username}!",
            ephemeral=True
        )
        
        # Disable buttons in parent view
        for item in self.parent_view.children:
            item.disabled = True
        await interaction.message.edit(view=None)  # Remove point selection buttons
        
        # Try to edit the original validation message
        try:
            original_message = await channel.fetch_message(interaction.message.reference.message_id if interaction.message.reference else interaction.message.id)
            await original_message.edit(view=self.parent_view)
        except:
            pass
        
        globals.log_message(message=f"[HarperBot] {interaction.user} marked answer {self.answer_index} as correct for user {self.user_id} - {points} points awarded")


class PaginationView(discord.ui.View):
    def __init__(self, pages, timeout=180):
        super().__init__(timeout=timeout)
        self.pages = pages
        self.current_page = 0
        self.max_pages = len(pages)
        
        # Disable buttons if only one page
        if self.max_pages <= 1:
            self.previous_button.disabled = True
            self.next_button.disabled = True
        else:
            self.previous_button.disabled = True  # Disable on first page

    @discord.ui.button(label="◀️ Previous", style=discord.ButtonStyle.gray)
    async def previous_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        if self.current_page > 0:
            self.current_page -= 1
            
            # Update button states
            self.previous_button.disabled = (self.current_page == 0)
            self.next_button.disabled = False
            
            await interaction.response.edit_message(embed=self.pages[self.current_page], view=self)

    @discord.ui.button(label="Next ▶️", style=discord.ButtonStyle.gray)
    async def next_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        if self.current_page < self.max_pages - 1:
            self.current_page += 1
            
            # Update button states
            self.next_button.disabled = (self.current_page == self.max_pages - 1)
            self.previous_button.disabled = False
            
            await interaction.response.edit_message(embed=self.pages[self.current_page], view=self)


class QuestionCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.questions_sent = 0  # Fixed: Made it an instance variable
        self.questions = {
            ## ECONOMY
            1: "A member claims they lost 50k currency due to a bot glitch. They have proof via screenshot. How would you handle this?",
            2: "Someone wants you to add 1 billion currency to their account because they're a content creator. What's your response?",
            3: "The server economy is inflated - everyone has billions. What commands would you suggest to them inorder fix this?",
            4: "A member accidentally bought 100 of an expensive item. They want a refund. What will you do?",
            5: "Someone's complaining that te leaderboard shows members who left the server 6 months ago. How do you fix this?",
            6: "A user asks why they can see everyone else's balance but others can't see theirs. What setting controls this?",
            7: "The server owner want new members to start with 5000 coins in their bank. How do you set this up?",
            8: "Someone's asking why they only earn 50-100 currency in their server while others earn 500-1000 in a different server. What would you suggest them?",
            9: "A member wants their economy data completely removed from the server. What command handles this?",
            10: "A trusted member asks you to give them 10k as a 'loan' they'll pay back. What's the appropriate response?",
            11: "Someone's complaining they can't deposit money in their bank. What setting do you need to check?",
            12: "A member sold an item to another member outside the bot, but wants you to transfer the money. Should you?",
            13: "The owner wants to change the currency from coins to gems. How do you do this?",
            14: "Someone wants to hide themselves from the leaderboard for privacy. Is this possible and how?",
            15: "If a user request you to give them free eldorium or blazecoins, what's your response?",
            
            ## ITEM MANAGEMENT
            16: "A member bought a VIP Role item but didn't receive the role. What do you check first?",
            17: "The shop has an item priced at 100 currency that should be 100k. How do you fix this?",
            18: "Someone wants to create an item that removes a role instead of giving one. Is this possible?",
            19: "An item's description has a typo. What's the command to fix just the description?",
            20: "The owner wants an item to have unlimited stock instead of the current limit of 50. How do you change this?",
            21: "A limited edition item should only be buyable by people with the Premium role. How do you set this up?",
            22: "Someone accidentally bought an item meant for another member. Can you transfer it between their inventories?",
            23: "An item's emoji is displaying incorrectly. How would you remove it or change it?",
            24: "The owner wants to see all custom items in the server before deciding which to remove. What command shows this?",
            25: "A member wants you to create an item that costs 0 currency. Is this allowed and how would you explain it?",
            
            ## COMMAND CONFIGURATION
            26: "Members are complaining that rob cooldown is too short - people get robbed every hour. How do you increase it?",
            27: "Someone's asking why they can't use the slots command in #general but can use it in #casino. What controls this?",
            28: "The owner wants to disable all gambling commands server-wide. What's the fastest way?",
            29: "Work command pays too little - members want it increased to 1000-5000 per use. How do you set this?",
            30: "Someone says blackjack has no maximum bet and people are betting billions. How do you add a limit?",
            31: "The rob success rate is 60% and the owner wants it lowered to 30%. What command do you use?",
            32: "Members can use bot commands in every channel and it's getting spammy. How do you restrict it to specific channels?",
            33: "The owner wants grab-jobs to appear more frequently. What setting controls this?",
            34: "Someone's asking why the minimum bet for dice is 10 currency. They want it raised to 100. How do you change this?",
            35: "Work command cooldown is 24 hours and members say it's too long. Owner agrees to reduce it to 12 hours. How?",
            36: "The owner wants member nicknames to show on leaderboards instead of usernames. What command changes this?",
            37: "Chat money system should give 10-50 currency every 5 messages. How would you enable and configure this?",
            
            ## PERMISSION & AUTHORITY
            38: "A moderator is asking why they can't use add-money command even though they have Manage Server permission. What's missing?",
            39: "The owner wants specific trusted members to use admin economy commands without giving them Administrator. How?",
            40: "Someone with Authority role accidentally reset the entire server economy. How could this have been prevented?",
            41: "A staff member wants to know what permissions they need to create giveaways. What do you tell them?",
            42: "You need to remove someone from the Authority list because they're abusing commands. How?",
            43: "The owner is asking what's the difference between Authority and Administrator permission for bot commands. How do you explain?",
            44: "A staff member can use toggle-module but not set-prefix. Why might this be?",
            45: "Someone's asking if they need special permissions to view the server's current tax settings. What's the answer?",
            
            ## ADVANCED FEATURES
            46: "The owner wants a lottery system where members can buy tickets. How would you set this up?",
            47: "Members with Gold role should earn 5000 coins automatically every 24 hours. What command enables this?",
            48: "The owner wants add-money and remove-money actions logged to a specific channel. How do you set this up?",
            49: "Someone's asking if they can create custom job responses for the grab-job feature. Is this possible?",
            50: "The owner wants the default grab-jobs disabled but custom ones enabled. How do you configure this?",
            51: "Bank limit is currently 100k and the owner wants different limits for different roles. Is this possible with these commands?",
            52: "The owner wants counting channel to restart from 1 if someone messes up. How do you set this up?",
            53: "Someone's asking how to make work command replies more personalized for the server theme. What command helps?",
            54: "The owner wants purchase logs enabled but add-money logs disabled. How do you configure this separately?",
            55: "Members want to know current tax settings before they deposit money. What command shows this information?",
            
            ## PROBLEM-SOLVING & POLICY
            56: "A member is demanding you give them items/money in the eldoria server because other servers do it. How do you respond professionally?",
            57: "Someone found a way to exploit grab-jobs by creating alt accounts. What immediate action do you take?",
            58: "Two members are fighting because one robbed the other for 50k. Both are demanding you intervene. What do you do?",
            59: "The leaderboard shows someone with 999 trillion currency, which seems impossible. What do you investigate?",
            60: "A member threatens to report the server if you don't give them compensation for lost currency with no proof. How do you handle this?",
            
            # GENERAL MODERATION
            61: "A user is spamming the same message across multiple channels. What's your immediate action, and what follow-up steps would you take?",
            62: "Two members are having a heated argument in a public channel. The discussion is getting personal but hasn't violated any explicit rules yet. How do you handle this?",
            63: "A new member joins and immediately starts posting NSFW content in a SFW channel. What's your response?",
            64: "You notice a member has changed their username to something offensive. What do you do?",
            65: "Someone reports that another user sent them threatening DMs. The reporter provides screenshots. How do you proceed?",
            66: "A popular member with a good history violates a minor rule for the first time. How do you balance fairness with their standing in the community?",
            67: "Multiple users are reporting the same person for 'being annoying' but you can't find any rule violations. What's your approach?",
            68: "You see a suspicious link being shared. How do you determine if it's malicious and what actions do you take?",
            
            69: "What information should you document when issuing a warning or ban?",
            70: "When should you escalate an issue to senior moderators or admins versus handling it yourself?",
            71: "A user appeals their ban and claims they were unfairly punished. What's your process for reviewing this?",
            72: "How do you handle a situation where you personally dislike a user but they haven't broken any rules?",
            73: "What's the difference between a timeout, a kick, and a ban? When would you use each?",
            74: "Should moderators explain their actions publicly, in DMs, or both? What are the pros and cons?",
            75: "How would you handle discovering that another moderator abused their power?",
            
            76: "What's the purpose of Discord's AutoMod feature and what are its limitations?",
            77: "How can you tell if a user is using an alt account to evade a ban?",
            78: "What Discord permissions should a moderator have, and which ones are unnecessary?",
            79: "How do slow mode and verification levels help with moderation?",
            80: "What's the difference between deleting messages and timing someone out?",
            
            81: "How do you balance strict rule enforcement with maintaining a welcoming community atmosphere?",
            82: "A long-time member is consistently bending the rules without technically breaking them. How do you address this?",
            83: "What would you do if community members start complaining that moderation is too strict or too lenient?",
            84: "How should moderators interact with the community when not actively moderating?",
            85: "Someone is asking for mental health advice or expressing suicidal thoughts. What's your response?"
        }
        self.question_task.start()

    def cog_unload(self):
        self.question_task.cancel()

    @tasks.loop(seconds=SPAWN_INTERVAL)  # Fixed: Use constant initial value
    async def question_task(self):
        await self.bot.wait_until_ready()
        
        # Fetch all channels from the category
        channels = await fetch_channels_from_category(self.bot)
        
        if not channels:
            globals.log_message(error="No channels found in the category")
            return
        
        # Randomly select a channel from the category
        channel = random.choice(channels)
        globals.log_message(message=f"[HarperBot] Selected channel: {channel.name} for question")

        question_id = random.choice(list(self.questions.keys()))
        question_text = self.questions[question_id]
        self.questions.pop(question_id)
        question_data = {
            "id": question_id,
            "question": question_text
        }
        
        # Create improved embed
        embed = discord.Embed(
            title="🎯 Moderator Question",
            description=question_data['question'],
            color=discord.Color.blue()
        )
        embed.add_field(
            name="📝 Instructions",
            value="Click the button below to submit your answer. Maximum 500 characters.",
            inline=False
        )
        embed.set_footer(text=f"Question #{question_id} • Answer thoughtfully!")
        
        view = discord.ui.View()
        view.add_item(AnswerButton(question_data))
        await channel.send(embed=embed, view=view)
        
        self.questions_sent += 1  # Fixed: Use self.questions_sent
        globals.log_message(message=f"[HarperBot] Sent question {self.questions_sent}/{TOTAL_QUESTIONS}")
        
        # Check if we've sent all questions AFTER sending
        if self.questions_sent >= TOTAL_QUESTIONS:
            self.question_task.stop()
            globals.log_message(message=f"[HarperBot] Reached {TOTAL_QUESTIONS} questions. Stopping task.")
            return
        
        # Change interval for next iteration
        self.question_task.change_interval(seconds=get_random_spawn_time())

    @question_task.before_loop
    async def before_question_task(self):
        await self.bot.wait_until_ready()

    @app_commands.command(name="points", description="View the points leaderboard")
    async def points(self, interaction: discord.Interaction):
        try:
            if interaction.user.id != OWNER_ID:
                await interaction.response.send_message("❌ You are not authorized to use this command!", ephemeral=True)
                return

            embed = discord.Embed(
                title="📊 Points Leaderboard",
                description="Here are the scores of all participants:",
                color=discord.Color.blue()
            )
            
            if not user_scores:
                embed.description = "No scores yet! Answer some questions to get started."
            else:
                # Sort by score descending
                sorted_scores = sorted(user_scores.items(), key=lambda x: x[1], reverse=True)
                
                for rank, (user_id, score) in enumerate(sorted_scores, 1):
                    user = self.bot.get_user(user_id)
                    username = user.display_name if user else f"User {user_id}"
                    medal = "🥇" if rank == 1 else "🥈" if rank == 2 else "🥉" if rank == 3 else f"{rank}."
                    embed.add_field(
                        name=f"{medal} {username}",
                        value=f"**{score}** points",
                        inline=False
                    )
            
            await interaction.response.send_message(embed=embed)
        except Exception as e:
            globals.log_message(error=e)
            await interaction.response.send_message("❌ An error occurred while fetching points.", ephemeral=True)

    @app_commands.command(name="view-answers", description="View all answers submitted")
    async def view_answers(self, interaction: discord.Interaction):
        try:
            if interaction.user.id != OWNER_ID:
                await interaction.response.send_message("❌ You are not authorized to use this command!", ephemeral=True)
                return
            
            if not user_answers:
                embed = discord.Embed(
                    title="📝 Submitted Answers",
                    description="No answers submitted yet!",
                    color=discord.Color.blue()
                )
                await interaction.response.send_message(embed=embed, ephemeral=True)
                return
            
            # Collect all answers with user info
            all_answers = []
            for user_id, answers in user_answers.items():
                user = self.bot.get_user(user_id)
                username = user.display_name if user else f"User {user_id}"
                for idx, answer in enumerate(answers, 1):
                    all_answers.append({
                        "user_id": user_id,
                        "username": username,
                        "index": idx,
                        "question_id": answer["id"],
                        "question": answer["question"],
                        "answer": answer["answer"]
                    })
            
            # Create pages (10 answers per page)
            ANSWERS_PER_PAGE = 10
            pages = []
            
            for i in range(0, len(all_answers), ANSWERS_PER_PAGE):
                embed = discord.Embed(
                    title="📝 Submitted Answers",
                    description=f"Showing answers {i+1}-{min(i+ANSWERS_PER_PAGE, len(all_answers))} of {len(all_answers)}",
                    color=discord.Color.blue()
                )
                
                page_answers = all_answers[i:i+ANSWERS_PER_PAGE]
                for ans in page_answers:
                    # Get validation status
                    status = validation_status.get(ans["user_id"], {}).get(ans["index"], None)
                    if status == "correct":
                        status_emoji = "✅"
                    elif status == "wrong":
                        status_emoji = "❌"
                    else:
                        status_emoji = "⏳"
                    
                    # Truncate answer if too long
                    answer_preview = ans["answer"]
                    if len(answer_preview) > 100:
                        answer_preview = answer_preview[:100] + "..."
                    
                    embed.add_field(
                        name=f"{status_emoji} {ans['username']} - Q{ans['question_id']} (Answer #{ans['index']})",
                        value=f"**Q:** {ans['question'][:80]}{'...' if len(ans['question']) > 80 else ''}\n**A:** {answer_preview}",
                        inline=False
                    )
                
                embed.set_footer(text=f"Page {len(pages)+1}/{(len(all_answers)-1)//ANSWERS_PER_PAGE + 1} • Use buttons to navigate")
                pages.append(embed)
            
            # Send with pagination
            view = PaginationView(pages)
            await interaction.response.send_message(embed=pages[0], view=view, ephemeral=True)
            
        except Exception as e:
            globals.log_message(error=e)
            await interaction.response.send_message("❌ An error occurred while fetching answers.", ephemeral=True)

    @app_commands.command(name="validate-answer", description="Validate answers for a specific question")
    @app_commands.describe(question_id="The question ID to validate answers for")
    async def validate_answer(self, interaction: discord.Interaction, question_id: int):
        try:
            if interaction.user.id != OWNER_ID:
                await interaction.response.send_message("❌ You are not authorized to use this command!", ephemeral=True)
                return
            
            # Check if question ID is valid
            if question_id not in self.questions:
                await interaction.response.send_message(
                    f"❌ Invalid question ID! Please use a question ID between 1 and {len(self.questions)}.",
                    ephemeral=True
                )
                return
            
            # Find all answers for this question
            answers_for_question = []
            for user_id, answers in user_answers.items():
                for idx, answer in enumerate(answers, 1):
                    if answer["id"] == question_id:
                        answers_for_question.append({
                            "user_id": user_id,
                            "answer_index": idx,
                            "answer": answer["answer"]
                        })
            
            # If no answers found
            if not answers_for_question:
                embed = discord.Embed(
                    title="❌ Not Answered",
                    description=f"**Question ID:** {question_id}\n\n**Question:**\n{self.questions[question_id]}\n\n**Status:** No one has answered this question yet.",
                    color=discord.Color.red()
                )
                await interaction.response.send_message(embed=embed, ephemeral=True)
                return
            
            # Create pages for multiple answers
            pages = []
            for ans_data in answers_for_question:
                user = self.bot.get_user(ans_data["user_id"])
                username = user.display_name if user else f"User {ans_data['user_id']}"
                
                # Check if already validated
                status = validation_status.get(ans_data["user_id"], {}).get(ans_data["answer_index"], None)
                status_text = ""
                if status == "correct":
                    status_text = "\n\n**⚠️ This answer has already been marked as CORRECT**"
                elif status == "wrong":
                    status_text = "\n\n**⚠️ This answer has already been marked as WRONG**"
                
                embed = discord.Embed(
                    title="📋 Answer Validation",
                    description=f"**User:** {user.mention if user else username}\n**Answer Index:** {ans_data['answer_index']}{status_text}",
                    color=discord.Color.gold()
                )
                embed.add_field(
                    name=f"Question ID: {question_id}",
                    value=self.questions[question_id],
                    inline=False
                )
                embed.add_field(
                    name="📝 Answer",
                    value=ans_data["answer"],
                    inline=False
                )
                embed.add_field(
                    name="🎯 Scoring",
                    value="✅ **Correct:** 2-5 points (you choose)\n❌ **Wrong:** 1 point",
                    inline=False
                )
                embed.set_footer(text=f"Current Score: {user_scores.get(ans_data['user_id'], 0)} points | Answer {len(pages)+1}/{len(answers_for_question)}")
                
                pages.append({
                    "embed": embed,
                    "user_id": ans_data["user_id"],
                    "answer_index": ans_data["answer_index"]
                })
            
            # Send first answer with validation buttons
            view = ValidationView(pages[0]["user_id"], pages[0]["answer_index"])
            
            # If multiple answers, add navigation info
            if len(pages) > 1:
                pages[0]["embed"].add_field(
                    name="ℹ️ Multiple Answers",
                    value=f"This question has {len(pages)} answers. Validate this one, then run the command again to see others.",
                    inline=False
                )
            
            await interaction.response.send_message(embed=pages[0]["embed"], view=view)

        except Exception as e:
            globals.log_message(error=e)
            await interaction.response.send_message("❌ An error occurred while validating the answer.", ephemeral=True)

    @validate_answer.autocomplete('question_id')
    async def question_id_autocomplete(
        self,
        interaction: discord.Interaction,
        current: str,
    ) -> list[app_commands.Choice[int]]:
        # Get all answered question IDs
        answered_questions = set()
        for user_id, answers in user_answers.items():
            for answer in answers:
                answered_questions.add(answer["id"])
        
        # Convert to sorted list
        answered_questions = sorted(list(answered_questions))
        
        # Filter based on current input
        if current:
            try:
                current_int = int(current)
                filtered = [q for q in answered_questions if str(q).startswith(str(current_int))]
            except ValueError:
                filtered = answered_questions
        else:
            filtered = answered_questions
        
        # Return up to 25 choices (Discord limit)
        choices = []
        for q_id in filtered[:25]:
            # Count how many users answered this question
            answer_count = sum(1 for user_id, answers in user_answers.items() 
                             for answer in answers if answer["id"] == q_id)
            
            # Truncate question text for display
            question_preview = self.questions[q_id]
            if len(question_preview) > 60:
                question_preview = question_preview[:60] + "..."
            
            choices.append(
                app_commands.Choice(
                    name=f"Q{q_id}: {question_preview} ({answer_count} answer{'s' if answer_count != 1 else ''})",
                    value=q_id
                )
            )
        
        return choices


class AnswerButton(discord.ui.Button):
    def __init__(self, question: dict):
        super().__init__(label="Submit Answer", style=discord.ButtonStyle.primary, emoji="✍️")
        self.question = question

    async def callback(self, interaction: discord.Interaction):
        modal = QuestionModal(self.question)
        await interaction.response.send_modal(modal)


async def setup(bot: commands.Bot):
    await bot.add_cog(QuestionCog(bot))