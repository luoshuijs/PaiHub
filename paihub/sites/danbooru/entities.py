from paihub.entities.artwork import ArtWork
from paihub.entities.author import Author


class DanbooruUploader(Author):
    @property
    def url(self) -> str:
        return f"https://danbooru.donmai.us/users/{self.auther_id}"


class DanbooruArtWork(ArtWork):
    web_name: str = "Danbooru"
    author: DanbooruUploader
    is_sourced: bool = True

    @property
    def url(self) -> str:
        return f"https://danbooru.donmai.us/posts/{self.artwork_id}"
