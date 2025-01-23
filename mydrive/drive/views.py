from django.shortcuts import render

import os
import json
import uuid

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.parsers import MultiPartParser

from mydrive.settings import USERS_JSON_FILE, USER_FILES_DIR, BASE_DIR


class RegisterView(APIView):

    def post(self, request):
        user_email = request.data.get('user_email')
        if not user_email:
            return Response({'error': 'Email is required'}, status=status.HTTP_400_BAD_REQUEST)
        
        json_file_path = USERS_JSON_FILE

        if os.path.exists(json_file_path):
            with open(json_file_path, 'r') as file:
                users = json.load(file)
        else:
            users = []

        if any(user['email'] == user_email for user in users):
            return Response({'error': 'user already exists'}, status=status.HTTP_400_BAD_REQUEST)
        
        user_id = str(uuid.uuid4())
        new_user = {'id': user_id, 'email': user_email}
        users.append(new_user)

        with open(json_file_path, 'w') as file:
            json.dump(users, file, indent=4)

        user_folder_path = os.path.join(USER_FILES_DIR, user_id)
        os.makedirs(user_folder_path, exist_ok=True)

        return Response({'user_id': user_id}, status=status.HTTP_201_CREATED) 


class FileUploadView(APIView):
    parser_classes = [MultiPartParser]

    def post(self, request):
        user_id = request.data.get('user_id')
        uploaded_file = request.FILES.get('file')
        sub_path = request.data.get("sub_path", "").strip()

        if not user_id or not uploaded_file:
            return Response({'error': 'user_id and file is required'}, status=status.HTTP_400_BAD_REQUEST)
        
        user_folder_path = os.path.join(USER_FILES_DIR, user_id)
        file_path = os.path.join(user_folder_path, sub_path, uploaded_file.name)

        if os.path.exists(file_path):
            base_name, extention = os.path.splitext(uploaded_file.name)
            counter = 1
            while os.path.exists(file_path):
                new_file_name = f'{base_name}({counter}){extention}'
                file_path = os.path.join(user_folder_path, new_file_name)
                counter += 1

        with open(file_path, 'wb') as file:
            for chunk in uploaded_file.chunks():
                file.write(chunk)   
            
        return Response({'message': 'File uploaded successfully', 'file_name': uploaded_file.name}, status=status.HTTP_201_CREATED)
        

class AddFolderView(APIView):

    def post(self, request):
        user_id = request.data.get('user_id')
        folder_name = request.data.get('folder_name')

        if not folder_name or not user_id:
            return Response({'error': 'user_id and folder_name is required'}, status=status.HTTP_400_BAD_REQUEST) 

        else:
            user_folder_path = os.path.join(USER_FILES_DIR, user_id)
            new_folder_path = os.path.join(user_folder_path, folder_name)
            os.makedirs(new_folder_path, exist_ok=True)

        return Response({'message': f'Новая папка создана по пути: {new_folder_path}'}, status=status.HTTP_201_CREATED) 


class UserFolderTreeView(APIView):
    def post(self, request):
        user_id = request.data.get('user_id')
        sub_path = request.data.get("sub_path", "").strip()

        user_folder_path = os.path.join(USER_FILES_DIR, user_id)
        folder_path = os.path.join(user_folder_path, sub_path)

        if not user_id:
            return Response({'error': 'user_id is required'}, status=status.HTTP_400_BAD_REQUEST) 
        
        if not os.path.exists(user_folder_path):
            return Response(
                {'error': f'Папка пользователя {user_id} не найдена!'}, 
                status=status.HTTP_404_NOT_FOUND
            )

        folder_tree = self.build_tree(folder_path)

        return Response({'folder_tree': folder_tree}, status=status.HTTP_200_OK)

    def build_tree(self, folder_path):
        tree = {}
        try:
            # Получаем список всех элементов в папке
            for entry in os.listdir(folder_path):
                full_path = os.path.join(folder_path, entry)
                # Если это папка, рекурсивно добавляем ее содержимое
                if os.path.isdir(full_path):
                    tree[entry] = self.build_tree(full_path)
                else:
                    # Если это файл, добавляем его как строку
                    tree[entry] = "file"
        except Exception as e:
            tree = {"error": str(e)}
        return tree