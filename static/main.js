
try {
    var token =  document.getElementById('token').innerHTML;
    localStorage.setItem('jwt-token', token)
  }
  catch(err) {
   
  }
var app = new Vue({
    el: '#app',
    delimiters: ['{', '}'],
    data: {
        message : 'hello',
        current_user: '',
        current_followers: [],
        current_followings:[],
        current_follower_count :0,
        current_following_count:0,
        current_posts:0,
        requested_user:'',
        requested_followers: [],
        requested_followings:[],
        requested_follower_count :0,
        requested_following_count:0,
        requested_posts:0,
        pfplink :'',
        usernames:[],
        links:[],
        len_usernames:0,
        posts_ids:[],
        posts_usernames:[],
        posts_pfplinks:[],
        posts_imglinks:[],
        posts_captions:[],
        flag:'0',
        bio:'',
        formerror:'',
        checkObjInArr : function(){
            console.log(this.current_user)
            return this.requested_followers.includes(this.current_user)
       },
       
    },

    mounted: async function(){
        
        var headers = {
            'Content-Type': 'application.json',
            'Authorization': '' + localStorage.getItem('jwt-token')
        }

        const gResponse1 = await fetch("http://192.168.131.156:8080/getcurrentuser",{
            method: 'GET',
            headers: headers,
        }
        );
        const gObject1 = await gResponse1.json();
        this.current_user = gObject1.user;

        const gResponse2 = await fetch("http://192.168.131.156:8080/getrequestedfollowers",{
            method: 'GET',
            headers: headers,
        });
        const gObject2 = await gResponse2.json();
        this.requested_followers = gObject2.followers;
        this.requested_followings = gObject2.followings;
        this.requested_follower_count = gObject2.follower_count;
        this.requested_following_count = gObject2.following_count;
        this.requested_posts=gObject2.posts;

        const gResponse6 = await fetch("http://192.168.131.156:8080/getcurrentfollowers",{
            method: 'GET',
            headers: headers,
        });
        const gObject6 = await gResponse6.json();
        this.current_followers = gObject6.followers;
        this.current_followings = gObject6.followings;
        this.current_follower_count = gObject6.follower_count;
        this.current_following_count = gObject6.following_count;
        this.current_posts=gObject6.posts;

        const gResponse3 = await fetch("http://192.168.131.156:8080/getpfp",{
            method: 'GET',
            headers: headers,
        });
        const gObject3 = await gResponse3.json();
        this.pfplink = gObject3.pfplink;
        this.requested_user = gObject3.requested_user;

        const gResponse4 = await fetch("http://192.168.131.156:8080/getsearchresults",{
            method: 'GET',
            headers: headers,
        });
        const gObject4 = await gResponse4.json();
        this.len_usernames = (gObject4.usernames).length;
        this.usernames = gObject4.usernames;
        this.links = gObject4.links;

        const gResponse5 = await fetch("http://192.168.131.156:8080/getpostinfo",{
            method: 'GET',
            headers: headers,
        });
        const gObject5 = await gResponse5.json();
        this.posts_usernames = gObject5.posts_usernames;
        this.posts_pfplinks = gObject5.posts_pfplinks;
        this.posts_imglinks = gObject5.posts_imglinks;
        this.posts_captions = gObject5.posts_captions;
        this.posts_ids = gObject5.posts_ids;
        
        const gResponse7 = await fetch("http://192.168.131.156:8080/getbio",{
            method: 'GET',
            headers: headers,
        });
        const gObject7 = await gResponse7.json();
        this.bio = gObject7.bio;

    }
})