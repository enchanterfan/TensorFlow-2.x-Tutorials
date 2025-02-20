import  os
os.environ['TF_CPP_MIN_LOG_LEVEL'] = '2'
import  numpy as np
import  tensorflow as tf
from    tensorflow import keras 
from	PIL import Image
import  glob
from    gan import Generator, Discriminator

from    dataset import make_anime_dataset


def save_result(val_out, val_block_size, image_path, color_mode):
    def preprocess(img):
        img = ((img + 1.0) * 127.5).astype(np.uint8)
        # img = img.astype(np.uint8)
        return img

    preprocesed = preprocess(val_out)
    final_image = np.array([])
    single_row = np.array([])
    for b in range(val_out.shape[0]):
        # concat image into a row
        if single_row.size == 0:
            single_row = preprocesed[b, :, :, :]
        else:
            single_row = np.concatenate((single_row, preprocesed[b, :, :, :]), axis=1)

        # concat image row to final_image
        if (b+1) % val_block_size == 0:
            if final_image.size == 0:
                final_image = single_row
            else:
                final_image = np.concatenate((final_image, single_row), axis=0)

            # reset single row
            single_row = np.array([])

    if final_image.shape[2] == 1:
        final_image = np.squeeze(final_image, axis=2) 
    Image.fromarray(final_image).save(image_path)


def celoss_ones(logits):
    # [b, 1]
    # [b] = [1, 1, 1, 1,]
    loss = tf.nn.sigmoid_cross_entropy_with_logits(logits=logits,
                                                   labels=tf.ones_like(logits))
    # 此处的logits并不是真实的logits，而是我们自己指定的模拟的，所以这个标签全都是1，即假定全部都是送的真的。     
    return tf.reduce_mean(loss)


def celoss_zeros(logits):
    # [b, 1]
    # [b] = [1, 1, 1, 1,]
    loss = tf.nn.sigmoid_cross_entropy_with_logits(logits=logits,
                                                   labels=tf.zeros_like(logits))
    # 此处是人为模拟的全部送的都是假的图片的loss，默认所有label都是0。    
    return tf.reduce_mean(loss)

def d_loss_fn(generator, discriminator, batch_z, batch_x, is_training):
    # 1. treat real image as real
    # 2. treat generated image as fake
    fake_image = generator(batch_z, is_training)
    d_fake_logits = discriminator(fake_image, is_training)
    d_real_logits = discriminator(batch_x, is_training)

    d_loss_real = celoss_ones(d_real_logits)
    d_loss_fake = celoss_zeros(d_fake_logits)

    loss = d_loss_fake + d_loss_real
    # 总的loss等于判别器对真的loss加上判别器对假的loss。 
    return loss


def g_loss_fn(generator, discriminator, batch_z, is_training):

    fake_image = generator(batch_z, is_training)
    d_fake_logits = discriminator(fake_image, is_training)
    loss = celoss_ones(d_fake_logits)
    # 生成器的loss主要任务是尽可能的骗过鉴别器，所以会希望d_fake_logits尽可能的大，而celoss_ones(d_fake_logits)尽可能的小，即分类结果为1的损失率尽可能小。
    return loss

def main():

    tf.random.set_seed(22)
    np.random.seed(22)
    assert tf.__version__.startswith('2.')


    # hyper parameters
    z_dim = 100
    epochs = 3000000
    batch_size = 512
    learning_rate = 0.002
    is_training = True


    img_path = glob.glob(r'C:\Users\Jackie\Downloads\faces\*.jpg')
    assert len(img_path) > 0

    dataset, img_shape, _ = make_anime_dataset(img_path, batch_size)
    print(dataset, img_shape)
    sample = next(iter(dataset))
    print(sample.shape, tf.reduce_max(sample).numpy(),
          tf.reduce_min(sample).numpy())
    dataset = dataset.repeat()
    db_iter = iter(dataset)
    # db_iter = iter(dataset)本意是只将dataset迭代一次，但是dataset = dataset.repeat()决定了只要当前的dataset迭代完，就继续往深处迭代，直到整个dataset真正的迭代完为止。

    generator = Generator()
    generator.build(input_shape = (None, z_dim))
    discriminator = Discriminator()
    discriminator.build(input_shape=(None, 64, 64, 3))

    g_optimizer = tf.keras.optimizers.Adam(learning_rate=learning_rate, beta_1=0.5)
    d_optimizer = tf.keras.optimizers.Adam(learning_rate=learning_rate, beta_1=0.5)


    for epoch in range(epochs):

        batch_z = tf.random.normal([batch_size, z_dim])
        batch_x = next(db_iter)
        # train D
        with tf.GradientTape() as tape:
            d_loss = d_loss_fn(generator, discriminator, batch_z, batch_x, is_training)
        grads = tape.gradient(d_loss, discriminator.trainable_variables)
        # 鉴别器的loss是为了尽可能的识别出假的图片，尽可能的将其识别为0。         
        d_optimizer.apply_gradients(zip(grads, discriminator.trainable_variables))


        batch_z = tf.random.normal([batch_size, z_dim])
        with tf.GradientTape() as tape:
            g_loss = g_loss_fn(generator, discriminator, batch_z, is_training)
        grads = tape.gradient(g_loss, generator.trainable_variables)
        # 生成器的loss是为了尽可能的骗过鉴别器，让其识别为1         
        g_optimizer.apply_gradients(zip(grads, generator.trainable_variables))

        if epoch % 100 == 0:
            print(epoch, 'd-loss:',float(d_loss), 'g-loss:', float(g_loss))

            z = tf.random.normal([100, z_dim])
            fake_image = generator(z, training=False)
            img_path = os.path.join('images', 'gan-%d.png'%epoch)
            save_result(fake_image.numpy(), 10, img_path, color_mode='P')



if __name__ == '__main__':
    main()
