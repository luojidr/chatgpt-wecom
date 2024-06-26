from wecom.utils.reply import MessageReply
from wecom.apps.worktool.models.author_delivery import AuthorDelivery
from wecom.apps.worktool.models.script_delivery import ScriptDelivery
from wecom.utils.template import AuthorTemplate, AuthorContent
from wecom.utils.template import TopAuthorNewWorkTemplate, TopAuthorNewWorkContent


class DeliveryAuthor:
    def push(self):
        results = AuthorDelivery.get_required_author_delivery_list()

        for group_name, objects in results.items():
            ids = []
            templates = []

            for obj in objects:
                ids.append(obj.id)
                templates.append(
                    AuthorTemplate(
                        author=obj.author, works_name=obj.work_name,
                        theme=obj.theme, platform=obj.platform,
                        brief=obj.brief, src_url=obj.src_url
                    )
                )

            AuthorDelivery.update_push_by_ids(ids)

            content = AuthorContent(templates).get_layout_content()
            MessageReply(group_remark=group_name).simple_push(content=content, receiver="所有人", max_length=700)


class DeliveryScript:
    def push(self):
        results = ScriptDelivery.get_required_script_delivery_list()

        for group_name, objects in results.items():
            templates = []
            uniq_ids = []

            for obj in objects:
                templates.append(
                    TopAuthorNewWorkTemplate(
                        author=obj.author, works_name=obj.work_name,
                        theme=obj.theme, core_highlight=obj.core_highlight,
                        core_idea=obj.core_idea,
                        pit_date=obj.pit_date, ai_score=obj.ai_score,
                        detail_url=obj.detail_url, src_url=obj.src_url
                    )
                )
                uniq_ids.append(obj.uniq_id)

            if uniq_ids:
                ScriptDelivery.update_push(uniq_ids)

                content = TopAuthorNewWorkContent(templates).get_layout_content()
                MessageReply(group_remark=group_name).simple_push(content=content, receiver="所有人", max_length=700)
