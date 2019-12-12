
from datetime import datetime
from praw.models import MoreComments
from subprocess import call, check_output
from urllib.request import urlopen

import constants
import praw
import json
import re

upvote_icon = '\u2b06'
POST_LIMIT = 5
COMMENT_LIMIT = 5
PROFILE_LIMIT = 5

def time_diff(created):
	minutes = (datetime.now().timestamp() - created) / 60.0
	return "{}m".format(round(minutes))

def get_profile_comments(me, limit=50):
	comments = me.comments.new(limit=limit)
	arr = []
	for idx, comment in enumerate(comments):
		arr.append({"idx": idx, "score": comment.score, "body": comment.body})
	return arr

def read_subreddit(reddit, sub, default_filter="rising"):
	if default_filter == "rising":
		reddit_posts = reddit.subreddit(sub).rising(limit=40)
	elif default_filter == "top":
		reddit_posts = reddit.subreddit(sub).top('hour', limit=40)
	else:
		reddit_posts = reddit.subreddit(sub).new(limit=40)
	posts = []
	for post in reddit_posts:
		posts.append({"id": post.id, "title": post.title, "score": post.score, "comments": post.num_comments, "created": post.created_utc, "url": post.url})	
	print_posts(posts)
	return posts

def read_post(reddit, post_id):
	post = reddit.submission(id=post_id)
	post.comment_sort = "top"
	comments = post.comments.list()
	print_comments(comments[:COMMENT_LIMIT])
	return comments

def read_profile_comments(comments, default_filter):
	#comments =
	if default_filter == "top":
		pass

def print_seperator(fh=None, cnt=40):
	if fh:
		fh.write('-'*cnt)
	else:
		print('-'*cnt)

def print_comment(idx, comment, end="\n\t"):
	print("{}:\t{}{} {}\n".format(idx, comment.score, upvote_icon, comment.body.replace("\n", end)))

def print_comment_to_fh(fh, score, body):
	print_seperator(fh=fh, cnt=80)
	fh.write("\n{}{} {}\n\n".format(score, upvote_icon, body.replace("\\n", "\n")))

def print_comments(comments):
	print("\n")
	for idx in range(COMMENT_LIMIT - 5, COMMENT_LIMIT):
		if idx >= len(comments):
			continue
		print_comment(idx, comments[idx])
	return

def print_profile_comments(comments):
	print("\n")
	for idx in range(PROFILE_LIMIT - 5, PROFILE_LIMIT):
		if idx >= len(posts):
			continue
		print("{}:\t{}{} {}\n".format(idx, comments[idx]["score"], upvote_icon, comments[idx]["body"].replace("\n", "\n\t")))
	return

def print_posts(posts):
	print("\n")
	for idx in range(POST_LIMIT - 5, POST_LIMIT):
		if idx >= len(posts):
			continue
		print_post(idx, posts[idx])
	return

def print_post(idx, post):
	print("{}:\t{}\n\t{} | {} comments | {}{}\n\t{}\n".format(idx, post["title"], time_diff(post["created"]), post["comments"], post["score"], upvote_icon, post["url"]))

def print_profile(reddit):
	me = reddit.user.me()
	print("\n{}\t{} link\t{} comment".format(me.name, me.link_karma, me.comment_karma))
	print_seperator()

	profile_comments = get_profile_comments(me)
	PROFILE_LIMIT = 5
	print_profile_comments(profile_comments)
	return profile_comments

def download_profile_comments(reddit):
	comments = reddit.user.me().comments.top(limit=None)
	out = ""
	for idx, comment in enumerate(comments):
		out += "{};;{};;{};;{}\n".format(comment.id, comment.created_utc, comment.score, comment.body.replace("\n", "\\n"))
	with open("comments.txt", "w") as fh:
		fh.write(out)

def query_profile(reddit, query):
	res = check_output(["grep", "-i", query, "comments.txt"])
	# last el is always empty
	comments = res.decode("utf-8").split("\n")[:-1]
	call(["rm", "-f", "query.txt"])
	query_file = open("query.txt", "w")
	query_file.write("\n\t{} results found\n".format(len(comments)))
	for comment in comments:
		data = comment.split(";;")
		print_comment_to_fh(query_file, data[2], data[3]) # score, body
	query_file.close()
	call(["vim", "query.txt"])

def print_unread(reddit):
	for idx, item in enumerate(reddit.inbox.all(limit=5)):
		print_comment(idx, item)

def profile_loop(reddit):
	profile_comments = print_profile(reddit)
	command = ""
	default_filter = "rising"
	while command not in ["b", "back"]:
		print("(b)ack, (f)ilter, (d)ownload, (u)nread, (r)efresh, (q)uery, (l)ess, (m)ore, or (e)xit: ", end="")
		command = input()
		command_split = command.split(" ")
		command = command_split[0]
		if command in ["e", "exit"]:
			exit()
		elif command in ["r", "refresh"]:
			profile_comments = print_profile(reddit)
		elif command in ["u", "unread"]:
			print_unread(reddit)
		elif command in ["q", "query"]:
			query = " ".join(command_split[1:])
			query_profile(reddit, query)
		elif command in ["d", "download"]:
			download_profile_comments(reddit)
		elif command in ["f", "filter"]:
			default_filter = command_split[1]
			PROFILE_LIMIT = 5
			posts = read_subreddit(reddit, default_sub, default_filter)
		elif command in ["m", "more"]:
			if PROFILE_LIMIT + 5 < len(profile_comments):
				PROFILE_LIMIT += 5
				print_profile_comments(profile_comments)
		elif command in ["l", "less"]:
			if PROFILE_LIMIT - 5 > 0:
				PROFILE_LIMIT += 5
				print_profile_comments(profile_comments)


def post_comment(post, comment):
	submission = reddit.submission(id=post["id"])
	submission.reply(comment)
	print("Commented")

def post_reply(comment_data, txt):
	comment = reddit.comment(id=comment_data.id)
	comment.reply(txt)
	print("Replied")

def comment_loop(comments, comment_idx):
	comment = comments[comment_idx]
	replies = comment.replies
	print("\n")
	print_comment(comment_idx, comment)
	print_seperator()
	for idx, reply in enumerate(replies):
		print("\t", end="")
		print_comment(idx, reply, end="\n\t\t")

		if isinstance(reply, MoreComments):
			print("MORE COMMENTS")
			continue

	command = ""
	stop_cmds = ["e", "exit", "b", "back", "q", "quit", "p", "profile"]
	while command not in stop_cmds:
		print("(p)rofile, (r)eply comment, (c)omment, (b)ack, (l)ess, (m)ore, or (e)xit: ", end="")
		command = input()
		command_split = command.split(" ")
		command = command_split[0]
		if command in ["c", "comment", "r", "reply"]:
			call(["rm", "-f", "reply.txt"])
			call(["vim", "reply.txt"])
			reply = open("reply.txt").read()
			if reply:
				if command in ["c", "comment"]:
					post_reply(comment, reply)
				else:
					comment_idx = int(command_split[1])
					post_reply(replies[comment_idx], reply)

	if command in ["e", "exit", "q", "quit"]:
		exit()
	elif command in ["b", "back"]:
		print_comments(comments)


if __name__ == '__main__':
	reddit = praw.Reddit(
		client_id=constants.ACCESS,
		client_secret=constants.SECRET, password=constants.PASSWORD,
		user_agent='by /u/intersecting_lines', username='intersecting_lines'
	)
	default_sub = "askreddit"
	default_filter = "rising"
	posts = read_subreddit(reddit, default_sub)
	command = ""
	while command not in ["e", "exit"]:
		print("(p)rofile, (r)ead post, refresh, (c)hange sub, (f)ilter, (l)ess, (m)ore, or (e)xit: ", end="")
		command = input()
		command_split = command.split(" ")
		command = command_split[0]
		if command in ["e", "exit", "q", "quit"]:
			exit()
		elif command == "refresh":
			POST_LIMIT = 5
			posts = read_subreddit(reddit, default_sub, default_filter)
		elif command in ["c", "change"]:
			default_sub = command_split[1]
			POST_LIMIT = 5
			posts = read_subreddit(reddit, default_sub, default_filter)
		elif command in ["f", "filter"]:
			default_filter = command_split[1]
			POST_LIMIT = 5
			posts = read_subreddit(reddit, default_sub, default_filter)
		elif command in ["p", "profile"]:
			profile_loop(reddit)
			print_posts(posts)
		elif command in ["m", "more"]:
			if POST_LIMIT + 5 < len(posts):
				POST_LIMIT += 5
				print_posts(posts)
		elif command in ["l", "less"]:
			if POST_LIMIT - 5 > 0:
				POST_LIMIT -= 5
				print_posts(posts)
		else:
			# read post
			post_idx = 0
			try:
				if command in ["r", "read"]:
					post_idx = int(command_split[1])
				else:
					post_idx = int(command)
			except:
				continue
			print("\n")
			COMMENT_LIMIT = 5
			print_post(post_idx, posts[post_idx])
			comments = read_post(reddit, posts[post_idx]["id"])
			stop_cmds = ["e", "exit", "b", "back", "q", "quit", "p", "profile"]
			while command not in stop_cmds:
				print("(p)rofile, (r)eply comment, (s)how comment, (c)omment, (b)ack, (l)ess, (m)ore, or (e)xit: ", end="")
				command = input()
				command_split = command.split(" ")
				command = command_split[0]
				if command in ["m", "more"]:
					if COMMENT_LIMIT + 5 < len(posts):
						COMMENT_LIMIT += 5
						print_comments(comments)
				elif command in ["l", "less"]:
					if COMMENT_LIMIT - 5 > 0:
						COMMENT_LIMIT -= 5
						print_comments(comments)
				elif command in ["c", "comment", "r", "reply"]:
					call(["rm", "-f", "reply.txt"])
					call(["vim", "reply.txt"])
					reply = open("reply.txt").read()
					if reply:
						if command in ["c", "comments"]:
							post_comment(posts[post_idx], reply)
						else:
							comment_idx = int(command_split[1])
							post_reply(comments[comment_idx], reply)
						
				else:
					# show comment or a number was entered
					comment_idx = 0
					try:
						if command in ["s", "show"]:
							comment_idx = int(command_split[1])
						else:
							comment_idx = int(command)
					except:
						continue
					comment_loop(comments, comment_idx)

			if command in ["b", "back"]:
				print_posts(posts)
			elif command in ["p", "profile"]:
				profile_loop(reddit)
				print_posts(posts)





