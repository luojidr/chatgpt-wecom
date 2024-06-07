from flask import Blueprint, request, jsonify
from flask_login import login_required

blueprint = Blueprint("user", __name__, url_prefix="/users", static_folder="../static")


@blueprint.route("/")
# @login_required
def members():
    """List members."""
    # print(type(request))
    # print('__dict__:', request.__dict__)
    #
    # for attr in dir(request):
    #     if not attr.startswith('_'):
    #         print(attr, ' -> ', getattr(request, attr))

    return jsonify(msg="Welcome to Flask Cookiecutter!")
    # return render_template("users/members.html")

#
# @blueprint.route('/post', methods=['POST'])
# def test_post():
#     print(type(request))
#     print('__dict__:', request.__dict__)
#     print('dir:', dir(request))
#
#     return jsonify()
